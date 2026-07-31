import os
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

# Thread pool for async execution
executor = ThreadPoolExecutor(max_workers=2)

# =========================================================
# HELPER: GET COOKIES
# =========================================================

def _get_cookies_path():
    """Reads YOUTUBE_COOKIES env var and returns a temp file path."""
    cookies_content = os.environ.get('YOUTUBE_COOKIES')
    if not cookies_content:
        return None

    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            f.write(cookies_content)
            return f.name
    except Exception as e:
        print(f"⚠️ Error creating cookies file: {e}")
        return None

# =========================================================
# CORE YT-DLP EXECUTOR
# =========================================================

async def _run_ytdl(url: str, download: bool = True, extract_flat: bool = False):
    """Internal function to run yt-dlp asynchronously."""
    cookies_path = _get_cookies_path()
    
    ydl_opts = {
        'format': 'bestaudio/best',  # Audio focus (you can change to bestvideo+bestaudio if needed)
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        },
        'extract_flat': extract_flat
    }

    try:
        loop = asyncio.get_running_loop()
        
        def sync_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=download)

        info = await loop.run_in_executor(executor, sync_download)
        return info, None

    except Exception as e:
        return None, str(e)
    
    finally:
        if cookies_path and os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
            except:
                pass

# =========================================================
# 1. SEARCH FUNCTION (Provider calls this)
# =========================================================

async def search(query: str, limit: int = 10):
    """
    Searches and downloads the video/audio from the URL.
    Returns a format compatible with Provider.search()
    """
    info, error = await _run_ytdl(query, download=True, extract_flat=False)
    
    if error:
        return {
            "success": False,
            "error": error
        }

    if not info:
        return {
            "success": False,
            "error": "No information retrieved from YouTube."
        }

    # Format the response to match what provider expects
    return {
        "success": True,
        "results": [{
            "id": info.get('id'),
            "title": info.get('title'),
            "duration": info.get('duration'),
            "uploader": info.get('uploader'),
            "url": info.get('webpage_url'),
            "source": "youtube"
        }],
        "total": 1
    }

# =========================================================
# 2. GET INFO FUNCTION (Provider calls this)
# =========================================================

async def get_info(item_id: str):
    """
    Fetches metadata without downloading the file.
    """
    url = f"https://www.youtube.com/watch?v={item_id}"
    info, error = await _run_ytdl(url, download=False, extract_flat=False)
    
    if error or not info:
        return {"success": False, "error": error or "Failed to fetch info"}

    return {
        "success": True,
        "data": {
            "id": info.get('id'),
            "title": info.get('title'),
            "duration": info.get('duration'),
            "uploader": info.get('uploader'),
            "thumbnail": info.get('thumbnail'),
            "url": info.get('webpage_url')
        }
    }

# =========================================================
# 3. DOWNLOAD SONG FUNCTION (Provider calls this)
# =========================================================

async def download_song(video_id: str, bitrate: int = 320, download_location: str = None):
    """
    Directly downloads the song (audio) and returns the file path.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Override options for pure audio download
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_location or ""}%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': _get_cookies_path(),
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        loop = asyncio.get_running_loop()
        
        def sync_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)

        info = await loop.run_in_executor(executor, sync_download)
        
        if not info:
            return {"success": False, "error": "Download failed"}

        # Get the downloaded file path
        requested_downloads = info.get('requested_downloads', [])
        filepath = requested_downloads[0].get('filepath') if requested_downloads else None

        return {
            "success": True,
            "filepath": filepath,
            "title": info.get('title')
        }

    except Exception as e:
        return {"success": False, "error": str(e)}