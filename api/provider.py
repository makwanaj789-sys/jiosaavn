import logging
from typing import Any, Dict, Optional

# SIRF YOUTUBE IMPORT
from api.youtube import download_video

logger = logging.getLogger(__name__)

class Provider:

    def __init__(self):
        self.youtube = download_video

    # =====================================
    # SEARCH (Sirf YouTube)
    # =====================================

    async def search(
        self,
        query: str,
        page_size: int = 10
    ) -> Any:

        response = await self.youtube(query)

        if not response or not response.get("success"):
            return []

        return response.get("results", [])

    # =====================================
    # DOWNLOAD SONG (Sirf YouTube)
    # =====================================

    async def download_song(
        self,
        item_id: str,
        bitrate: int = 320,
        download_location: str = None
    ):

        # Agar item_id URL nahi hai toh URL bana do
        if not item_id.startswith("http"):
            url = f"https://www.youtube.com/watch?v={item_id}"
        else:
            url = item_id

        return await self.youtube(url)