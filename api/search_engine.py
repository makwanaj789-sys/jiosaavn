import os
import tempfile
import asyncio
import yt_dlp
import re
import uuid
import logging

logger = logging.getLogger(__name__)

def is_url(text):
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/'
    return re.match(youtube_regex, text) is not None

def _get_cookies_file():
    """Create cookies file from environment variable"""
    cookies_data = os.environ.get('YOUTUBE_COOKIES')
    if not cookies_data:
        logger.warning("⚠️ YOUTUBE_COOKIES not found in environment!")
        return None

    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            delete=False,
            suffix='.txt'
        ) as f:
            f.write(cookies_data)
            logger.info("✅ Cookies file created successfully")
            return f.name
    except Exception as e:
        logger.error(f"⚠️ Error creating cookies file: {e}")
        return None

class SearchEngine:
    def __init__(self):
        # 🔥 COOKIES SUPPORT ADD KARO
        self.cookies_path = _get_cookies_file()
        
        self.ydl_opts_search = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch10",
            "geo_bypass": True,
            "extract_flat": True,
            "skip_download": True,
            "cookiefile": self.cookies_path,  # 🔥 COOKIES ADD
        }
        
        self.ydl_opts_download = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "geo_bypass": True,
            "extract_flat": False,
            "outtmpl": os.path.join(tempfile.gettempdir(), "%(title)s.%(ext)s"),
            "cookiefile": self.cookies_path,  # 🔥 COOKIES ADD
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
        
        logger.info(f"✅ SearchEngine initialized with cookies: {self.cookies_path is not None}")

    async def search(self, query: str, search_type: str = "songs", page_size: int = 10):
        """
        Search for songs on YouTube
        Returns 10 results by default
        """
        try:
            if not is_url(query):
                final_query = f"ytsearch{page_size}:{query}"
            else:
                final_query = query

            loop = asyncio.get_running_loop()
            
            def sync_search():
                with yt_dlp.YoutubeDL(self.ydl_opts_search) as ydl:
                    info = ydl.extract_info(final_query, download=False)
                    return info

            info = await loop.run_in_executor(None, sync_search)

            if not info:
                return {"results": [], "total": 0}

            if "entries" in info:
                entries = info.get("entries", [])
                results = []
                
                for entry in entries:
                    if entry:
                        results.append({
                            "id": entry.get("id"),
                            "title": entry.get("title", "Unknown"),
                            "duration": entry.get("duration", 0),
                            "uploader": entry.get("uploader", "Unknown Artist"),
                            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                            "source": "youtube"
                        })
                
                return {
                    "results": results,
                    "total": len(results)
                }
            else:
                return {
                    "results": [{
                        "id": info.get("id"),
                        "title": info.get("title", "Unknown"),
                        "duration": info.get("duration", 0),
                        "uploader": info.get("uploader", "Unknown Artist"),
                        "url": f"https://www.youtube.com/watch?v={info.get('id')}",
                        "source": "youtube"
                    }],
                    "total": 1
                }

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"results": [], "total": 0, "error": str(e)}

    async def download_song(self, item_id: str):
        """
        Download song from YouTube using video ID
        """
        try:
            url = f"https://www.youtube.com/watch?v={item_id}"
            
            loop = asyncio.get_running_loop()
            
            def sync_download():
                with yt_dlp.YoutubeDL(self.ydl_opts_download) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return info

            info = await loop.run_in_executor(None, sync_download)

            if not info:
                return {"success": False, "error": "No info found"}

            filepath = None
            if info.get("requested_downloads"):
                filepath = info["requested_downloads"][0].get("filepath")
            
            if not filepath:
                filepath = ydl.prepare_filename(info)
                
                base = os.path.splitext(filepath)[0]
                for ext in [".mp3", ".webm", ".m4a", ".opus"]:
                    candidate = base + ext
                    if os.path.exists(candidate):
                        filepath = candidate
                        break

            return {
                "success": True,
                "data": {
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", "Unknown"),
                    "filepath": filepath
                }
            }

        except Exception as e:
            logger.error(f"Download error: {e}")
            return {"success": False, "error": str(e)}
            
    def __del__(self):
        """Cleanup cookies file on object destruction"""
        if self.cookies_path and os.path.exists(self.cookies_path):
            try:
                os.remove(self.cookies_path)
                logger.info("🧹 Cookies file cleaned up")
            except:
                pass