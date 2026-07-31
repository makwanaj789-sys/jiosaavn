import os
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

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

# yt-dlp run karne ka internal function
async def _run_ytdl(url: str, download: bool = True):
    cookies_path = _get_cookies_path()
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,
        'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
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

# 1. Search function (Provider ke liye)
async def search(query: str, limit: int = 10):
    info, error = await _run_ytdl(query, download=True)
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

# 2. Get Info function (Provider ke liye)
async def get_info(item_id: str):
    url = f"https://www.youtube.com/watch?v={item_id}"
    info, error = await _run_ytdl(url, download=False)
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

# 3. Download function (Provider ke liye)
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