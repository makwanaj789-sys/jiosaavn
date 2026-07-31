import logging
from typing import Optional

from api.provider import Provider

logger = logging.getLogger(__name__)


class DownloadEngine:

    def __init__(self):
        self.provider = Provider()

    async def download(
        self,
        item_id: str,
        source: str = "jiosaavn",
        bitrate: int = 320,
        download_location: Optional[str] = None
    ):
        """
        Universal download entry point.
        """

        return await self.provider.download_song(
            item_id=item_id,
            source=source,
            bitrate=bitrate,
            download_location=download_location
        )