import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheManager:

    def __init__(self, db):
        self.db = db

    async def get(self, video_id: str):
        """
        Get cached song by YouTube video ID.
        """

        try:
            data = await self.db.music_cache.find_one(
                {
                    "video_id": video_id
                }
            )

            if not data:
                return None

            # Last used update
            await self.db.music_cache.update_one(
                {
                    "video_id": video_id
                },
                {
                    "$set": {
                        "last_used": datetime.utcnow()
                    },
                    "$inc": {
                        "hits": 1
                    }
                }
            )

            logger.info(f"⚡ CACHE HIT: {video_id}")

            return data

        except Exception as e:
            logger.error(f"Cache Get Error: {e}")
            return None

    async def save(
        self,
        video_id: str,
        file_id: str,
        title: str,
        duration: int,
        uploader: str
    ):
        """
        Save song in cache.
        """

        try:

            await self.db.music_cache.update_one(
                {
                    "video_id": video_id
                },
                {
                    "$set": {
                        "video_id": video_id,
                        "file_id": file_id,
                        "title": title,
                        "duration": duration,
                        "uploader": uploader,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow(),
                        "hits": 0
                    }
                },
                upsert=True
            )

            logger.info(f"💾 CACHE SAVED: {title}")

            return True

        except Exception as e:
            logger.error(f"Cache Save Error: {e}")
            return False

    async def delete(self, video_id: str):

        try:
            await self.db.music_cache.delete_one(
                {
                    "video_id": video_id
                }
            )

            logger.info(f"🗑 CACHE REMOVED: {video_id}")

        except Exception as e:
            logger.error(f"Cache Delete Error: {e}")