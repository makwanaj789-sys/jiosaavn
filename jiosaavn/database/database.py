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

        # Search counter
        self.search_collection = self.stats_db.searches

        # Groups where bot has been used
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

    # =========================================================
    # USER DATABASE
    # =========================================================

    @staticmethod
    def new_user(user_id: int) -> dict:
        """
        Creates a new user dictionary with default values.
        """

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
        """
        Checks if a user exists in the database.
        """

        user = await self.user_collection.find_one(
            {"id": user_id}
        )

        return bool(user)

    async def add_user(self, user_id: int):
        """
        Adds a new user to the database.
        """

        user = self.new_user(user_id)

        await self.user_collection.insert_one(user)

        return user

    async def get_user(self, user_id: int) -> dict:
        """
        Retrieves a user from the database.
        """

        user = await self.user_collection.find_one(
            {"id": user_id}
        )

        if not user:
            user = await self.add_user(user_id)

        return user

    async def update_user(
        self,
        user_id: int,
        key: str,
        value: any
    ):
        """
        Updates a user's information.
        """

        await self.user_collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    key: value
                }
            }
        )

    # =========================================================
    # SONG DATABASE
    # =========================================================

    async def is_song_id_exist(
        self,
        item_id: str
    ) -> bool:
        """
        Checks if a song ID exists.
        """

        item = await self.id_collection.find_one(
            {"id": item_id}
        )

        if not item:

            await self.id_collection.insert_one(
                {
                    "id": item_id,
                    "chat_id": 0,
                    "message_id": 0
                }
            )

        return bool(item)

    async def get_song(
        self,
        song_id: str
    ) -> dict:
        """
        Retrieves a song from the database.
        """

        song = await self.id_collection.find_one(
            {"id": song_id}
        )

        return song

    async def update_song(
        self,
        song_id: str,
        quality: str,
        chat_id: int,
        message_id: int
    ):
        """
        Updates a song's information.
        """

        update_fields = {
            f"{quality}.chat_id": chat_id,
            f"{quality}.message_id": message_id
        }

        await self.id_collection.update_one(
            {"id": song_id},
            {
                "$set": update_fields
            }
        )

    # =========================================================
    # SEARCH ANALYTICS
    # =========================================================

    async def add_search(
        self,
        user_id: int,
        chat_id: int = 0
    ):
        """
        Records one music search.

        We intentionally don't store the search text/query because
        the admin only needs aggregate statistics.
        """

        await self.search_collection.insert_one(
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "created_at": datetime.datetime.now(
                    datetime.timezone.utc
                )
            }
        )

    # =========================================================
    # GROUP TRACKING
    # =========================================================

    async def add_group(
        self,
        group_id: int
    ):
        """
        Saves a group only once.
        """

        await self.group_collection.update_one(
            {
                "id": group_id
            },
            {
                "$setOnInsert": {
                    "id": group_id,
                    "added_on": datetime.datetime.now(
                        datetime.timezone.utc
                    )
                }
            },
            upsert=True
        )

    # =========================================================
    # ADMIN STATISTICS
    # =========================================================

    async def get_admin_stats(self) -> dict:
        """
        Returns statistics for the admin panel.
        """

        now = datetime.datetime.now(
            datetime.timezone.utc
        )

        today = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        # Total unique users already stored by Aarti
        total_users = await self.user_collection.count_documents({})

        # Total groups tracked
        total_groups = await self.group_collection.count_documents({})

        # Total music searches
        total_searches = await self.search_collection.count_documents({})

        # Searches since 00:00 UTC
        searches_today = await self.search_collection.count_documents(
            {
                "created_at": {
                    "$gte": today
                }
            }
        )

        # Unique users who searched today
        active_users_today = await self.search_collection.distinct(
            "user_id",
            {
                "created_at": {
                    "$gte": today
                }
            }
        )

        return {
            "total_users": total_users,
            "total_groups": total_groups,
            "total_searches": total_searches,
            "searches_today": searches_today,
            "active_today": len(active_users_today)
        }