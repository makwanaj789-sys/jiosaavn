import logging
from typing import Dict, List, Any, Optional

# Hum provider ko direct import karenge
from api.provider import Provider

logger = logging.getLogger(__name__)

class SearchEngine:

    def __init__(self):
        self.provider = Provider()

    # ==========================================
    # SEARCH (Only YouTube)
    # ==========================================

    async def search(
        self,
        query: str,
        search_type: str = "songs",
        page_no: int = 1,
        page_size: int = 10
    ):

        # SIRF YOUTUBE SEARCH KARO
        result = await self.provider.search(
            query=query,
            page_size=page_size
        )

        # Agar result None ya list nahi hai toh empty return karo
        if not result or not isinstance(result, list):
            return {
                "results": [],
                "total": 0
            }

        # YouTube results ko normalize karo
        data = self._normalize_youtube(result)

        return {
            "results": data,
            "total": len(data)
        }

    # ==========================================
    # NORMALIZE YOUTUBE (Format conversion)
    # ==========================================

    def _normalize_youtube(
        self,
        results: List[Dict]
    ) -> List[Dict]:
        """YouTube results ko JioSaavn format mein convert karein taaki buttons theek dikhein."""
        
        if not results:
            return []

        data = []

        for item in results:
            if not item:
                continue

            video_id = item.get("id")
            if not video_id:
                continue

            title = item.get("title", "Unknown Title")
            artist = item.get("uploader", "Unknown Artist")
            duration = item.get("duration", 0)
            
            if duration:
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "N/A"

            thumbnail = item.get("thumbnail", "")
            perma_url = f"https://youtu.be/{video_id}"

            data.append({
                "id": video_id,
                "title": title,
                "artist": artist,
                "name": artist,
                "duration": duration,
                "duration_str": duration_str,
                "thumbnail": thumbnail,
                "url": perma_url,
                "perma_url": perma_url,
                "source": "youtube",  # Force source as YouTube
                "type": "song",
                "more_info": {
                    "album": artist,
                    "duration": duration_str,
                    "year": "YouTube"
                }
            })

        return data

    # ==========================================
    # DOWNLOAD SONG (Only YouTube)
    # ==========================================

    async def download_song(
        self,
        item_id: str,
        bitrate: int = 320,
        download_location: str = None
    ) -> Optional[str]:
        
        return await self.provider.download_song(
            item_id=item_id,
            bitrate=bitrate,
            download_location=download_location
        )