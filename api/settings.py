import logging

logger = logging.getLogger(__name__)

DEFAULTS = {
    "play_mode": "admins",   # "admins" or "everyone"
    "language": "en"
}


class SettingsManager:

    def __init__(self, db):
        self.db = db

    async def get(self, chat_id: int) -> dict:
        try:
            data = await self.db.chat_settings.find_one({"chat_id": chat_id})
            if not data:
                return DEFAULTS.copy()
            merged = DEFAULTS.copy()
            merged.update({k: v for k, v in data.items() if k in DEFAULTS})
            return merged
        except Exception as e:
            logger.error(f"Settings get error: {e}")
            return DEFAULTS.copy()

    async def set(self, chat_id: int, key: str, value):
        try:
            await self.db.chat_settings.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id, key: value}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Settings set error: {e}")
            return False

    async def get_play_mode(self, chat_id: int) -> str:
        s = await self.get(chat_id)
        return s.get("play_mode", "admins")