import logging
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