import os
import logging

logger = logging.getLogger(__name__)


class LocalCacheManager:

    def __init__(self, db):
        self.db = db

    async def get(self, video_id: str):
        """
        Returns filepath if it exists in DB AND still exists on disk.
        """
        try:
            data = await self.db.vc_file_cache.find_one({"video_id": video_id})
            if not data:
                return None

            filepath = data.get("filepath")
            if filepath and os.path.exists(filepath):
                return filepath

            # File was cached but no longer exists on disk — clean up entry
            await self.db.vc_file_cache.delete_one({"video_id": video_id})
            return None

        except Exception as e:
            logger.error(f"LocalCache get error: {e}")
            return None

    async def save(self, video_id: str, filepath: str):
        try:
            await self.db.vc_file_cache.update_one(
                {"video_id": video_id},
                {"$set": {"video_id": video_id, "filepath": filepath}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"LocalCache save error: {e}")