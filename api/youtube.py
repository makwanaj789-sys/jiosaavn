import os
import tempfile
import asyncio
import yt_dlp
import re

# Check karo ki query URL hai ya text
def is_url(text):
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/'
    return re.match(youtube_regex, text) is not None

# Cookies ko env se utha kar temp file banayega
def _get_cookies_file():
    cookies_data = os.environ.get('YOUTUBE_COOKIES')
    if not cookies_data:
        return None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            f.write(cookies_data)
            return f.name
    except Exception:
        return None

# Main Download / Search Function
async def download_video(query: str):
    cookies_path = _get_cookies_file()
    
    # 🔥 MAGIC LOGIC: Agar query URL nahi hai, toh "ytsearch:" prefix laga do
    if not is_url(query):
        final_query = f"ytsearch10:{query}"  # Top 10 results search karega
        download = False  # Search mode mein download nahi karna
    else:
        final_query = query
        download = True   # URL mode mein download karna hai
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,
        'extract_flat': not download, # Search mode mein flat extract karo
    }
    
    try:
        loop = asyncio.get_running_loop()
        def sync_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(final_query, download=download)
                return info
        
        info = await loop.run_in_executor(None, sync_download)
        
        # Agar URL tha (Single Video Download)
        if download:
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
            
        # Agar Text tha (Search Results)
        else:
            results = []
            entries = info.get('entries', [])
            if not entries:
                return {"success": False, "error": "No results found on YouTube"}
            
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
    finally:
        # Temporary cookies file clean karo
        if cookies_path and os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
            except:
                pass