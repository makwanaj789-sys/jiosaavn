# api/youtube.py

import logging
import os
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class YouTube:
    """YouTube API wrapper using YouTube Data API v3."""

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY", "")
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
        if not self.api_key:
            logger.error("⚠️ YOUTUBE_API_KEY not found! Set it in environment variables.")
        else:
            logger.info("✅ YouTube API key loaded successfully")

    # =============================================
    # SEARCH
    # =============================================

    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search YouTube videos."""
        
        if not self.api_key:
            logger.error("YouTube API key missing")
            return []

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoCategoryId": "10",  # Music category
            "maxResults": limit,
            "key": self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/search",
                    params=params,
                    timeout=15
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        results = self._parse_search_results(data)
                        logger.info(f"🎵 YouTube search: '{query}' -> {len(results)} results")
                        return results
                    else:
                        error_text = await response.text()
                        logger.error(f"YouTube API error: {response.status} - {error_text}")
                        return []

        except aiohttp.ClientError as e:
            logger.error(f"YouTube connection error: {e}")
            return []
        except Exception as e:
            logger.exception(f"YouTube search error: {e}")
            return []

    # =============================================
    # GET VIDEO INFO
    # =============================================

    async def get_info(
        self,
        video_id: str
    ) -> Optional[Dict]:
        """Get detailed video information."""
        
        if not self.api_key:
            logger.error("YouTube API key missing")
            return None

        params = {
            "part": "snippet,contentDetails",
            "id": video_id,
            "key": self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/videos",
                    params=params,
                    timeout=15
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("items", [])
                        if items:
                            video_info = self._parse_video_info(items[0])
                            logger.info(f"✅ Video info fetched: {video_info.get('title')}")
                            return video_info
                        else:
                            logger.warning(f"⚠️ Video not found: {video_id}")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"YouTube API error: {response.status} - {error_text}")
                        return None

        except Exception as e:
            logger.exception(f"Failed to get video info: {e}")
            return None

    # =============================================
    # DOWNLOAD SONG
    # =============================================

    async def download_song(
        self,
        video_id: str,
        bitrate: int = 320,
        download_location: str = None
    ) -> Optional[str]:
        """
        Download YouTube video as audio using yt-dlp.
        """
        
        try:
            import yt_dlp
        except ImportError:
            logger.error("❌ yt-dlp not installed")
            return None

        url = f"https://youtu.be/{video_id}"
        
        if not download_location:
            download_location = "downloads"
        
        os.makedirs(download_location, exist_ok=True)
        
        # yt-dlp options - optimized for audio download
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
            # Skip parts to avoid bot detection
            "extractor_args": {
                "youtube": {
                    "skip": ["dash", "hls"],
                }
            }
        }
        
        try:
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    filename = filename.rsplit(".", 1)[0] + ".mp3"
                    return filename
            
            file_path = await loop.run_in_executor(None, download)
            logger.info(f"✅ YouTube download success: {file_path}")
            return file_path
            
        except Exception as e:
            logger.exception(f"❌ YouTube download failed: {e}")
            return None

    # =============================================
    # PARSE HELPERS
    # =============================================

    def _parse_search_results(self, data: Dict) -> List[Dict]:
        """Parse YouTube search API response."""
        
        results = []
        items = data.get("items", [])
        
        for item in items:
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            
            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            
            # Get best thumbnail
            thumbnail = ""
            for quality in ["high", "medium", "default"]:
                if quality in thumbnails:
                    thumbnail = thumbnails[quality].get("url", "")
                    break
            
            results.append({
                "id": video_id,
                "title": snippet.get("title", "Unknown Title"),
                "uploader": snippet.get("channelTitle", "Unknown Artist"),
                "description": snippet.get("description", ""),
                "thumbnail": thumbnail,
                "url": f"https://youtu.be/{video_id}",
                "source": "youtube"
            })
        
        return results

    def _parse_video_info(self, video_data: Dict) -> Dict:
        """Parse YouTube video API response."""
        
        video_id = video_data.get("id", "")
        snippet = video_data.get("snippet", {})
        content_details = video_data.get("contentDetails", {})
        
        # Parse duration (ISO 8601 format)
        duration_str = content_details.get("duration", "PT0S")
        duration = self._parse_duration(duration_str)
        
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = ""
        for quality in ["high", "medium", "default"]:
            if quality in thumbnails:
                thumbnail = thumbnails[quality].get("url", "")
                break
        
        return {
            "id": video_id,
            "title": snippet.get("title", "Unknown Title"),
            "uploader": snippet.get("channelTitle", "Unknown Artist"),
            "description": snippet.get("description", ""),
            "duration": duration,
            "thumbnail": thumbnail,
            "url": f"https://youtu.be/{video_id}",
            "source": "youtube"
        }

    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        
        import re
        
        # Pattern: PT1H2M3S, PT1H, PT2M, PT3S, etc.
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds