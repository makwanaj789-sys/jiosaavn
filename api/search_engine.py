import logging
from typing import Dict, List, Any

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

        data = []

        for item in results:

            data.append({

                "id": item.get("id"),

                "title": item.get("title"),

                "artist": item.get("uploader"),

                "duration": item.get("duration"),

                "thumbnail": item.get("thumbnail"),

                "url": item.get("url"),

                "source": "youtube"

            })

        return data

    # ==========================================
    # SONG DETAILS
    # ==========================================

    async def get_song(
        self,
        item_id: str,
        source: str = "jiosaavn"
    ):

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
        album_id=None,
        playlist_id=None,
        page_no=1
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