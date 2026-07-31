import os
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
import re

executor = ThreadPoolExecutor(max_workers=2)

# Cookies uthane ka helper function
def _get_cookies_path():
    cookies_content = os.environ.get('YOUTUBE_COOKIES')
    if not cookies_content:
        return None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            f.write(cookies_content)
            return f.name
    except Exception:
        return None

# Helper to check if input is a URL
def is_url(text):
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/'
    return re.match(youtube_regex, text) is not None

# yt-dlp run karne ka internal function
async def _run_ytdl(url: str, download: bool = True, search_mode: bool = False):
    cookies_path = _get_cookies_path()
    
    # Agar search_mode True hai, toh 'ytsearch:' prefix laga do
    final_url = f"ytsearch10:{url}" if search_mode else url

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,
        'extract_flat': search_mode, # Search mode mein sirf list chahiye, download nahi
        'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    }
    try:
        loop = asyncio.get_running_loop()
        def sync_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(final_url, download=download)
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
# 🟢 1. UPDATED SEARCH FUNCTION (Text support ke sath)
# =========================================================

async def search(query: str, limit: int = 10):
    """
    Agar query URL hai toh download karega, nahi toh YouTube pe search karke results dikhayega.
    """
    
    # ✅ Check: Kya user ne URL daala hai ya Text?
    if is_url(query):
        # URL hai -> Direct video download karo
        info, error = await _run_ytdl(query, download=True, search_mode=False)
        if error or not info:
            return {"success": False, "error": error or "Failed"}
        
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
        
    else:
        # Text hai -> YouTube par search karo (Results dikhao)
        info, error = await _run_ytdl(query, download=False, search_mode=True)
        
        if error or not info:
            return {"success": False, "error": error or "No results found on YouTube."}
            
        results = []
        # yt-dlp search results ko 'entries' mein return karta hai
        entries = info.get('entries', [])
        for entry in entries:
            results.append({
                "id": entry.get('id'),
                "title": entry.get('title'),
                "duration": entry.get('duration'),
                "uploader": entry.get('uploader'),
                "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                "source": "youtube"
            })
            
        return {
            "success": True,
            "results": results,
            "total": len(results)
        }

# =========================================================
# 2. GET INFO FUNCTION 
# =========================================================

async def get_info(item_id: str):
    url = f"https://www.youtube.com/watch?v={item_id}"
    info, error = await _run_ytdl(url, download=False, search_mode=False)
    if error or not info:
        return {"success": False, "error": error or "Failed"}
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
# 3. DOWNLOAD SONG FUNCTION 
# =========================================================

async def download_song(video_id: str, bitrate: int = 320, download_location: str = None):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_location or ""}%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': _get_cookies_path(),
        'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    }
    try:
        loop = asyncio.get_running_loop()
        def sync_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)
        info = await loop.run_in_executor(executor, sync_download)
        if not info: return {"success": False, "error": "Failed"}
        filepath = info.get('requested_downloads', [{}])[0].get('filepath')
        return {"success": True, "filepath": filepath, "title": info.get('title')}
    except Exception as e:
        return {"success": False, "error": str(e)}