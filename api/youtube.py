import os
import sys
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

# Agar aapke paas logger hai toh use karein, warna print use karte hain
# import logging
# logger = logging.getLogger(__name__)

# Ek global thread pool (aap apni requirement ke hisaab se max_workers badha sakte hain)
executor = ThreadPoolExecutor(max_workers=2)

async def download_video(url: str):
    """
    Main function to download video from URL using yt-dlp with Cookies support.
    """
    cookies_path = None
    result = {"success": False, "data": None, "error": None}

    # 1. Environment variable se cookies ka data uthayein (Railway par set kiya hua)
    cookies_content = os.environ.get('YOUTUBE_COOKIES')
    
    # 2. Agar cookies milti hai, toh ek temporary file create karein
    if cookies_content:
        try:
            # delete=False zaroori hai kyunki yt-dlp ko file path chahiye hota hai
            # aur wo file tab tak exist karni chahiye jab tak download chal raha hai
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
                f.write(cookies_content)
                cookies_path = f.name
            print(f"✅ Cookies temporary file created: {cookies_path}")
        except Exception as e:
            print(f"⚠️ Error creating cookies file: {e}")
            cookies_path = None

    # 3. yt-dlp options set karein
    # Aap yahan 'format' ko apni requirement ke hisaab se change kar sakte hain
    ydl_opts = {
        # Audio/Video format. Ye best quality video + audio lega.
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
        'outtmpl': '%(title)s.%(ext)s',  # Output file ka naam
        'quiet': False,                  # False rakhoge toh Railway logs mein progress dikhega
        'no_warnings': False,    
        'ignoreerrors': True,
        'nooverwrites': True,
        
        # 🟢 IMPORTANT: Cookies file ka path pass karna
        'cookiefile': cookies_path,
        
        # Headers taaki ek real browser jaisa dikhe (YouTube bot detection se bachne ke liye)
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    try:
        # 4. Asynchronous execution (ThreadPoolExecutor use karke)
        loop = asyncio.get_running_loop()

        def download_sync():
            """Ye synchronous function background thread mein chalega"""
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # extract_info 'download=True' karega toh actual file download hogi
                info = ydl.extract_info(url, download=True)
                return info

        # Run the blocking download in a separate thread
        print(f"🚀 Starting download for: {url}")
        info = await loop.run_in_executor(executor, download_sync)
        
        # Download ho gayi, ab result prepare karein
        requested_downloads = info.get('requested_downloads', [])
        filepath = None
        if requested_downloads and len(requested_downloads) > 0:
            filepath = requested_downloads[0].get('filepath')

        result = {
            "success": True,
            "data": {
                "title": info.get('title'),
                "duration": info.get('duration'),
                "view_count": info.get('view_count'),
                "uploader": info.get('uploader'),
                "filepath": filepath
            },
            "error": None
        }
        print(f"✅ Download successful: {info.get('title')}")

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        print(f"❌ yt-dlp DownloadError: {error_msg}")
        
        # Agar cookies fail ho jayein toh specific message do
        if "Sign in to confirm" in error_msg:
            error_msg = "YouTube is blocking the request (Bot Detection). Check if the 'YOUTUBE_COOKIES' variable contains a valid, fresh cookies.txt from a logged-in account."
        
        result["error"] = error_msg

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        result["error"] = f"Internal Server Error: {str(e)}"

    finally:
        # 5. Clean up: Temporary cookies file ko delete kar dein
        if cookies_path and os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
                print(f"🧹 Cleaned up cookies temp file: {cookies_path}")
            except Exception as clean_error:
                print(f"⚠️ Could not delete temp file: {clean_error}")

    return result

# Agar aap isko seedha test karna chahte ho locally:
if __name__ == "__main__":
    async def main():
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        res = await download_video(test_url)
        print("\nFinal Result:", res)
    
    asyncio.run(main())