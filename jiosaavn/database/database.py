import datetime
import motor.motor_asyncio


class Database:
    def __init__(self, uri: str):
        """
        Initializes the Database instance with the provided URI.
        """

        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)

        # Existing databases
        self.user_db = self._client["jiosaavnV2_users"]
        self.id_db = self._client["jiosaavnV2_ids"]

        self.user_collection = self.user_db.users
        self.id_collection = self.id_db.ids

        # =====================================================
        # ADMIN ANALYTICS DATABASE
        # =====================================================

        self.stats_db = self._client["jiosaavnV2_stats"]
        self.search_collection = self.stats_db.searches
        self.group_collection = self.stats_db.groups

        # =====================================================
        # MUSIC CACHE DATABASE
        # =====================================================

        self.cache_db = self._client["jiosaavnV2_cache"]
        self.music_cache = self.cache_db.music_cache

        # =====================================================
        # FAVORITES DATABASE
        # =====================================================

        self.favorites_db = self._client["jiosaavnV2_favorites"]
        self.favorites = self.favorites_db.favorites

        # =====================================================
        # VOICE CHAT LOCAL FILE CACHE
        # =====================================================

        self.vc_cache_db = self._client["jiosaavnV2_vc_cache"]
        self.vc_file_cache = self.vc_cache_db.vc_file_cache

        # =====================================================
        # CHAT SETTINGS
        # =====================================================

        self.settings_db = self._client["jiosaavnV2_settings"]
        self.chat_settings = self.settings_db.chat_settings

    # =========================================================
    # USER DATABASE
    # =========================================================

    @staticmethod
    def new_user(user_id: int) -> dict:
        return {
            "id": user_id,
            "join_date": datetime.date.today().isoformat(),
            "type": "all",
            "quality": "320kbps",
            "ban_status": {
                "is_banned": False,
                "ban_duration": 0,
                "banned_on": datetime.date.max.isoformat(),
                "ban_reason": ""
            }
        }

    async def is_user_exist(self, user_id: int) -> bool:
        user = await self.user_collection.find_one({"id": user_id})
        return bool(user)

    async def add_user(self, user_id: int):
        user = self.new_user(user_id)
        await self.user_collection.insert_one(user)
        return user

    async def get_user(self, user_id: int) -> dict:
        user = await self.user_collection.find_one({"id": user_id})
        if not user:
            user = await self.add_user(user_id)
        return user

    async def update_user(self, user_id: int, key: str, value: any):
        await self.user_collection.update_one(
            {"id": user_id},
            {"$set": {key: value}}
        )

    async def delete_user(self, user_id: int):
        """Used by broadcast to drop users who blocked or deleted the bot."""
        await self.user_collection.delete_one({"id": user_id})

    async def get_all_users(self):
        """All stored user IDs — used for broadcasting."""
        return [
            doc["id"]
            async for doc in self.user_collection.find({}, {"id": 1})
            if doc.get("id")
        ]

    # =========================================================
    # SONG DATABASE
    # =========================================================

    async def is_song_id_exist(self, item_id: str) -> bool:
        item = await self.id_collection.find_one({"id": item_id})

        if not item:
            await self.id_collection.insert_one({
                "id": item_id,
                "chat_id": 0,
                "message_id": 0
            })

        return bool(item)

    async def get_song(self, song_id: str) -> dict:
        return await self.id_collection.find_one({"id": song_id})

    async def update_song(self, song_id: str, quality: str, chat_id: int, message_id: int):
        update_fields = {
            f"{quality}.chat_id": chat_id,
            f"{quality}.message_id": message_id
        }

        await self.id_collection.update_one(
            {"id": song_id},
            {"$set": update_fields}
        )

    # =========================================================
    # SEARCH ANALYTICS
    # =========================================================

    async def add_search(self, user_id: int, chat_id: int = 0, query: str = ""):
        """
        Records one music search. The query text is stored so the cache
        warmer can learn what people actually look for.
        """
        await self.search_collection.insert_one({
            "user_id": user_id,
            "chat_id": chat_id,
            "query": (query or "").lower().strip()[:100],
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        })

    async def top_queries(self, limit: int = 50, days: int = 14):
        """
        Most-searched queries from the last `days` days, most popular first.
        """
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": since},
                    "query": {"$nin": [None, ""]}
                }
            },
            {
                "$group": {
                    "_id": "$query",
                    "hits": {"$sum": 1}
                }
            },
            {"$sort": {"hits": -1}},
            {"$limit": limit}
        ]

        return [doc async for doc in self.search_collection.aggregate(pipeline)]

    # =========================================================
    # GROUP TRACKING
    # =========================================================

    async def add_group(self, group_id: int):
        await self.group_collection.update_one(
            {"id": group_id},
            {
                "$setOnInsert": {
                    "id": group_id,
                    "added_on": datetime.datetime.now(datetime.timezone.utc)
                }
            },
            upsert=True
        )

    async def delete_group(self, group_id: int):
        """Used by broadcast to drop groups the bot was removed from."""
        await self.group_collection.delete_one({"id": group_id})

    async def get_all_groups(self):
        """All stored group IDs — used for broadcasting."""
        return [
            doc["id"]
            async for doc in self.group_collection.find({}, {"id": 1})
            if doc.get("id")
        ]

    # =========================================================
    # ADMIN STATISTICS
    # =========================================================

    async def get_admin_stats(self) -> dict:
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_users = await self.user_collection.count_documents({})
        total_groups = await self.group_collection.count_documents({})
        total_searches = await self.search_collection.count_documents({})

        searches_today = await self.search_collection.count_documents({
            "created_at": {"$gte": today}
        })

        active_users_today = await self.search_collection.distinct(
            "user_id",
            {"created_at": {"$gte": today}}
        )

        return {
            "total_users": total_users,
            "total_groups": total_groups,
            "total_searches": total_searches,
            "searches_today": searches_today,
            "active_today": len(active_users_today)
        }