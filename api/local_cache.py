import os
import shutil
import logging

logger = logging.getLogger(__name__)

# 🔥 Dedicated permanent folder — not /tmp, so OS never auto-cleans it
PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vc_downloads"
)
os.makedirs(PERSIST_DIR, exist_ok=True)


class LocalCacheManager:

    def __init__(self, db):
        self.db = db

    async def get(self, video_id: str):
        try:
            data = await self.db.vc_file_cache.find_one({"video_id": video_id})
            if not data:
                return None

            filepath = data.get("filepath")
            if filepath and os.path.exists(filepath):
                return filepath

            await self.db.vc_file_cache.delete_one({"video_id": video_id})
            return None

        except Exception as e:
            logger.error(f"LocalCache get error: {e}")
            return None

    async def save(self, video_id: str, filepath: str):
        try:
            # Move the downloaded file into the permanent folder
            if os.path.exists(filepath) and not filepath.startswith(PERSIST_DIR):
                ext = os.path.splitext(filepath)[1]
                new_path = os.path.join(PERSIST_DIR, f"{video_id}{ext}")
                shutil.move(filepath, new_path)
                filepath = new_path

            await self.db.vc_file_cache.update_one(
                {"video_id": video_id},
                {"$set": {"video_id": video_id, "filepath": filepath}},
                upsert=True
            )
            return filepath

        except Exception as e:
            logger.error(f"LocalCache save error: {e}")
            return filepath