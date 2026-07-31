# api/provider.py

import logging
from typing import Any, Dict, Optional

from api.jiosaavn import Jiosaavn
from api.youtube import download_video

logger = logging.getLogger(__name__)


class Provider:

    def __init__(self):
        self.jiosaavn = Jiosaavn()
        self.youtube = YouTube()

    # =====================================
    # SEARCH
    # =====================================

    async def search(
        self,
        query: str,
        source: str = "jiosaavn",
        search_type: str = "songs",
        page_no: int = 1,
        page_size: int = 10
    ) -> Any:

        if source == "youtube":

            return await self.youtube.search(
                query=query,
                limit=page_size
            )

        return await self.jiosaavn.search(
            query=query,
            search_type=search_type,
            page_no=page_no,
            page_size=page_size
        )

    # =====================================
    # SEARCH ALL TYPES
    # =====================================

    async def search_all(
        self,
        query: str,
        source: str = "jiosaavn"
    ) -> Any:

        if source == "youtube":

            return await self.youtube.search(
                query=query,
                limit=10
            )

        return await self.jiosaavn.search_all_types(
            query=query
        )

    # =====================================
    # SONG DETAILS
    # =====================================

    async def get_song(
        self,
        item_id: str,
        source: str = "jiosaavn"
    ) -> Optional[Dict]:

        if source == "youtube":

            return await self.youtube.get_info(
                item_id
            )

        return await self.jiosaavn.get_song(
            item_id
        )

    # =====================================
    # ALBUM / PLAYLIST
    # =====================================

    async def get_playlist_or_album(
        self,
        album_id: str = None,
        playlist_id: str = None,
        page_no: int = 1,
        page_size: int = 10
    ):

        return await self.jiosaavn.get_playlist_or_album(
            album_id=album_id,
            playlist_id=playlist_id,
            page_no=page_no,
            page_size=page_size
        )

    # =====================================
    # ARTIST
    # =====================================

    async def get_artist(
        self,
        artist_id: str,
        page_no: int = 1,
        page_size: int = 10
    ):

        return await self.jiosaavn.get_artist(
            artist_id=artist_id,
            page_no=page_no,
            page_size=page_size
        )

    # =====================================
    # LYRICS
    # =====================================

    async def get_lyrics(
        self,
        lyrics_id: str
    ):

        return await self.jiosaavn.get_song_lyrics(
            lyrics_id
        )

    # =====================================
    # ⭐ DOWNLOAD - UPDATED
    # =====================================

    async def download_song(
        self,
        item_id: str,
        source: str = "jiosaavn",
        bitrate: int = 320,
        download_location: str = None
    ):

        if source == "youtube":
            return await self.youtube.download_song(
                video_id=item_id,
                bitrate=bitrate,
                download_location=download_location
            )

        return await self.jiosaavn.download_song(
            song_id=item_id,
            bitrate=bitrate,
            download_location=download_location
        )