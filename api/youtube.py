import os
import tempfile
import asyncio
import yt_dlp

# ---- Cookies ko Environment se utha kar file banane ka function ----
def _get_cookies_file():
    cookies_data = os.environ.get('YOUTUBE_COOKIES')
    if not cookies_data:
        return None
    
    try:
        # Ek temporary .txt file banao
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            f.write(cookies_data)
            return f.name
    except Exception:
        return None

# ---- Main Download Function (Ye hi provider use karta hai) ----
async def download_video(url: str):
    cookies_path = _get_cookies_file()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,  # <--- YAHAN COOKIES FILE KA PATH PASS HO RAHA HAI
    }
    
    try:
        # yt-dlp ko background thread mein chalao taaki bot block na ho
        loop = asyncio.get_running_loop()
        
        def sync_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        info = await loop.run_in_executor(None, sync_download)
        
        # Song ki details nikaalo
        filepath = None
        if info.get('requested_downloads'):
            filepath = info['requested_downloads'][0].get('filepath')

        return {
            "success": True,
            "data": {
                "title": info.get('title'),
                "duration": info.get('duration'),
                "uploader": info.get('uploader'),
                "filepath": filepath
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Temporary cookies file ko saaf kar do
        if cookies_path and os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
            except:
                pass