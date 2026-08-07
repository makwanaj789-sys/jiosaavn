import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FavoritesManager:

    def __init__(self, db):
        self.db = db

    async def add(self, user_id: int, video_id: str, title: str, file_id: str, uploader: str = ""):
        try:
            await self.db.favorites.update_one(
                {"user_id": user_id, "video_id": video_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "video_id": video_id,
                        "title": title,
                        "file_id": file_id,
                        "uploader": uploader,
                        "added_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            logger.info(f"❤️ FAVORITE ADDED: {title} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Favorites Add Error: {e}")
            return False

    async def remove(self, user_id: int, video_id: str):
        try:
            await self.db.favorites.delete_one(
                {"user_id": user_id, "video_id": video_id}
            )
            logger.info(f"💔 FAVORITE REMOVED: {video_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Favorites Remove Error: {e}")
            return False

    async def is_favorite(self, user_id: int, video_id: str) -> bool:
        try:
            data = await self.db.favorites.find_one(
                {"user_id": user_id, "video_id": video_id}
            )
            return data is not None
        except Exception as e:
            logger.error(f"Favorites Check Error: {e}")
            return False

    async def list_favorites(self, user_id: int, limit: int = 20):
        try:
            cursor = self.db.favorites.find(
                {"user_id": user_id}
            ).sort("added_at", -1).limit(limit)

            return [doc async for doc in cursor]
        except Exception as e:
            logger.error(f"Favorites List Error: {e}")
            return []