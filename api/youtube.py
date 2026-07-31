# api/youtube.py

import logging
import os
import asyncio
from typing import Dict, List, Optional, Any

import yt_dlp

logger = logging.getLogger(__name__)


class YouTube:

    def __init__(self):
        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "noplaylist": True,
        }

    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:

        search_query = f"ytsearch{limit}:{query}"

        try:

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:

                data = ydl.extract_info(
                    search_query,
                    download=False
                )

            results = []

            for item in data.get("entries", []):

                if not item:
                    continue

                results.append({

                    "id": item.get("id"),

                    "title": item.get("title"),

                    "duration": item.get("duration"),

                    "uploader": item.get("uploader"),

                    "thumbnail": item.get("thumbnail"),

                    "url": f"https://youtu.be/{item.get('id')}",

                    "source": "youtube"

                })

            return results

        except Exception as e:

            logger.exception(e)

            return []

    async def get_info(
        self,
        video_id: str
    ) -> Optional[Dict]:

        url = f"https://youtu.be/{video_id}"

        opts = {

            "quiet": True,

            "skip_download": True,

            "noplaylist": True,

        }

        try:

            with yt_dlp.YoutubeDL(opts) as ydl:

                info = ydl.extract_info(
                    url,
                    download=False
                )

            return info

        except Exception:

            logger.exception(
                "Failed to fetch youtube info"
            )

            return None

    # =============================================
    # ⭐ DOWNLOAD SONG - NEW FUNCTION
    # =============================================

    async def download_song(
        self,
        video_id: str,
        bitrate: int = 320,
        download_location: str = None
    ) -> Optional[str]:
        """
        Download YouTube video as audio.
        
        Args:
            video_id: YouTube video ID
            bitrate: Audio bitrate (128, 192, 256, 320)
            download_location: Custom download path
        
        Returns:
            Path to downloaded file or None if failed
        """
        
        url = f"https://youtu.be/{video_id}"
        
        # Set download location
        if not download_location:
            download_location = "downloads"
        
        # Create directory if not exists
        os.makedirs(download_location, exist_ok=True)
        
        # yt-dlp options for audio download
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(bitrate),
            }],
            "outtmpl": os.path.join(download_location, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_audio": True,
            "audio_format": "mp3",
            "audio_quality": bitrate,
            "writethumbnail": False,
        }
        
        try:
            # Run download in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    # Change extension to .mp3
                    filename = filename.rsplit(".", 1)[0] + ".mp3"
                    return filename
            
            file_path = await loop.run_in_executor(None, download)
            
            logger.info(f"YouTube download successful: {file_path}")
            return file_path
            
        except Exception as e:
            logger.exception(f"YouTube download failed: {e}")
            return None