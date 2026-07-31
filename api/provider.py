import logging
from typing import Any, Dict, Optional

# JioSaavn import (agar aapke paas ye file nahi hai toh ye line error dega, 
# lekin aapka bot YouTube ke liye tab bhi chalega)
try:
    from api.jiosaavn import Jiosaavn
    JIOSAAVN_AVAILABLE = True
except ImportError:
    JIOSAAVN_AVAILABLE = False

# YouTube ka function import karo (Jo abhi fix kiya hai)
from api.youtube import download_video

logger = logging.getLogger(__name__)


class Provider:

    def __init__(self):
        # JioSaavn initialize (agar available hai toh)
        if JIOSAAVN_AVAILABLE:
            self.jiosaavn = Jiosaavn()
        else:
            self.jiosaavn = None
            
        # YouTube function ko assign karo (bina brackets ke)
        self.youtube = download_video

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

        # Agar source YouTube hai toh YouTube ka function call karo
        if source == "youtube":
            return await self.youtube(query)

        # Agar JioSaavn hai toh JioSaavn ka function call karo
        if self.jiosaavn:
            return await self.jiosaavn.search(
                query=query,
                search_type=search_type,
                page_no=page_no,
                page_size=page_size
            )
        
        return {"error": "No source available"}

    # =====================================
    # SEARCH ALL TYPES
    # =====================================

    async def search_all(
        self,
        query: str,
        source: str = "jiosaavn"
    ) -> Any:

        if source == "youtube":
            return await self.youtube(query)

        if self.jiosaavn:
            return await self.jiosaavn.search_all_types(
                query=query
            )
        
        return {"error": "No source available"}

    # =====================================
    # SONG DETAILS
    # =====================================

    async def get_song(
        self,
        item_id: str,
        source: str = "jiosaavn"
    ) -> Optional[Dict]:

        if source == "youtube":
            # Agar aapke paas YouTube ke liye get_info function hai toh yahan call karein
            # Abhi ke liye simple response return kar rahe hain
            return {
                "title": "YouTube Song",
                "id": item_id,
                "source": "youtube"
            }

        if self.jiosaavn:
            return await self.jiosaavn.get_song(
                item_id
            )
        
        return None

    # =====================================
    # DOWNLOAD SONG
    # =====================================

    async def download_song(
        self,
        item_id: str,
        source: str = "jiosaavn",
        bitrate: int = 320,
        download_location: str = None
    ):

        if source == "youtube":
            # Agar YouTube ka URL hai toh direct download_video call karo
            # Note: Agar item_id sirf video ID hai toh URL bana lo
            if not item_id.startswith("http"):
                url = f"https://www.youtube.com/watch?v={item_id}"
            else:
                url = item_id
                
            return await self.youtube(url)

        if self.jiosaavn:
            return await self.jiosaavn.download_song(
                song_id=item_id,
                bitrate=bitrate,
                download_location=download_location
            )
        
        return {"error": "No source available"}