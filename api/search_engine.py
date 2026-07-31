import logging
from typing import Dict, List, Any, Optional

from api.provider import Provider

logger = logging.getLogger(__name__)


class SearchEngine:

    def __init__(self):
        self.provider = Provider()

    # ==========================================
    # SEARCH
    # ==========================================

    async def search(
        self,
        query: str,
        source: str = "jiosaavn",
        search_type: str = "songs",
        page_no: int = 1,
        page_size: int = 10
    ):

        # ======================================
        # ALL SEARCH
        # ======================================

        if search_type == "all":

            result = await self.provider.search_all(
                query=query,
                source=source
            )

            if source == "youtube":

                # Handle case when result is None or not a list
                if not result or not isinstance(result, list):
                    return {
                        "songs": {
                            "data": [],
                            "position": 1
                        },
                        "total": 0
                    }

                return {
                    "songs": {
                        "data": self._normalize_youtube(result),
                        "position": 1
                    }
                }

            # IMPORTANT:
            # Return original JioSaavn response
            return result

        # ======================================
        # NORMAL SEARCH
        # ======================================

        result = await self.provider.search(
            query=query,
            source=source,
            search_type=search_type,
            page_no=page_no,
            page_size=page_size
        )

        # ======================================
        # YOUTUBE
        # ======================================

        if source == "youtube":

            # Handle case when result is None or not a list
            if not result or not isinstance(result, list):
                return {
                    "results": [],
                    "total": 0
                }

            data = self._normalize_youtube(result)

            return {
                "results": data,
                "total": len(data)
            }

        # ======================================
        # JIOSAAVN
        # ======================================

        return result

    # ==========================================
    # NORMALIZE YOUTUBE
    # ==========================================

    def _normalize_youtube(
        self,
        results: List[Dict]
    ) -> List[Dict]:
        """Normalize YouTube results to match JioSaavn format."""
        
        if not results:
            return []

        data = []

        for item in results:
            if not item:
                continue

            video_id = item.get("id")
            if not video_id:
                continue

            # Get title
            title = item.get("title", "Unknown Title")
            
            # Get uploader/artist
            artist = item.get("uploader", "Unknown Artist")
            
            # Get duration
            duration = item.get("duration", 0)
            
            # Format duration
            if duration:
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "N/A"

            # Get thumbnail
            thumbnail = item.get("thumbnail", "")
            
            # Create YouTube URL
            perma_url = f"https://youtu.be/{video_id}"

            data.append({
                "id": video_id,
                "title": title,
                "artist": artist,
                "name": artist,  # For compatibility
                "duration": duration,
                "duration_str": duration_str,
                "thumbnail": thumbnail,
                "url": perma_url,
                "perma_url": perma_url,  # For compatibility
                "source": "youtube",
                "type": "song",
                "more_info": {
                    "album": artist,
                    "duration": duration_str,
                    "year": "YouTube"
                }
            })

        return data

    # ==========================================
    # SONG DETAILS
    # ==========================================

    async def get_song(
        self,
        item_id: str,
        source: str = "jiosaavn"
    ) -> Optional[Dict]:

        return await self.provider.get_song(
            item_id=item_id,
            source=source
        )

    # ==========================================
    # ARTIST
    # ==========================================

    async def get_artist(
        self,
        artist_id: str,
        page_no: int = 1
    ):

        return await self.provider.get_artist(
            artist_id=artist_id,
            page_no=page_no
        )

    # ==========================================
    # PLAYLIST / ALBUM
    # ==========================================

    async def get_playlist_or_album(
        self,
        album_id: str = None,
        playlist_id: str = None,
        page_no: int = 1
    ):

        return await self.provider.get_playlist_or_album(
            album_id=album_id,
            playlist_id=playlist_id,
            page_no=page_no
        )

    # ==========================================
    # LYRICS
    # ==========================================

    async def get_lyrics(
        self,
        lyrics_id: str
    ):

        return await self.provider.get_lyrics(
            lyrics_id
        )

    # ==========================================
    # ⭐ DOWNLOAD SONG - NEW METHOD
    # ==========================================

    async def download_song(
        self,
        item_id: str,
        source: str = "jiosaavn",
        bitrate: int = 320,
        download_location: str = None
    ) -> Optional[str]:
        """
        Download song from YouTube or JioSaavn.
        
        Args:
            item_id: Song/video ID
            source: "youtube" or "jiosaavn"
            bitrate: Audio bitrate (128, 192, 256, 320)
            download_location: Custom download path
        
        Returns:
            Path to downloaded file or None if failed
        """
        
        return await self.provider.download_song(
            item_id=item_id,
            source=source,
            bitrate=bitrate,
            download_location=download_location
        )