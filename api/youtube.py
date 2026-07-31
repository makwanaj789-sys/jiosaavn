import os
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

executor = ThreadPoolExecutor(max_workers=2)

# COOKIES FIX: Ye naya function cookies ko env se utha kar temp file banayega
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

# MAIN SEARCH FUNCTION (Aapka original search logic, bas cookies fix add kiya)
async def search(query: str, limit: int = 10):
    cookies_path = _get_cookies_path()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,  # <--- YAHAN COOKIES PASS KI
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        }
    }
    
    try:
        loop = asyncio.get_running_loop()
        def sync_search():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                return info
        
        info = await loop.run_in_executor(executor, sync_search)
        
        results = []
        entries = info.get('entries', [])
        if not entries:
            return {"success": False, "error": "No results found"}
            
        for entry in entries:
            results.append({
                "id": entry.get('id'),
                "title": entry.get('title'),
                "duration": entry.get('duration'),
                "uploader": entry.get('uploader'),
                "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                "source": "youtube"
            })
            
        return {"success": True, "results": results, "total": len(results)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# GET INFO
async def get_info(item_id: str):
    url = f"https://www.youtube.com/watch?v={item_id}"
    # Same yt-dlp logic (shortened for brevity)
    cookies_path = _get_cookies_path()
    ydl_opts = {'quiet': True, 'cookiefile': cookies_path}
    try:
        loop = asyncio.get_running_loop()
        def sync_get():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        info = await loop.run_in_executor(executor, sync_get)
        return {"success": True, "data": {"title": info.get('title'), "id": info.get('id'), "url": url}}
    except Exception as e:
        return {"success": False, "error": str(e)}

# DOWNLOAD SONG
async def download_song(video_id: str, bitrate: int = 320, download_location: str = None):
    url = f"https://www.youtube.com/watch?v={video_id}"
    cookies_path = _get_cookies_path()
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_location or ""}%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,  # <--- YAHAN BHI COOKIES PASS KI
    }
    try:
        loop = asyncio.get_running_loop()
        def sync_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)
        info = await loop.run_in_executor(executor, sync_dl)
        filepath = info.get('requested_downloads', [{}])[0].get('filepath')
        return {"success": True, "filepath": filepath, "title": info.get('title')}
    except Exception as e:
        return {"success": False, "error": str(e)}