import os
import asyncio
import logging

from api.search_engine import SearchEngine
from api.cache import CacheManager

logger = logging.getLogger(__name__)

STORAGE_CHAT_ID = -1003713614798
class InlineHelper:

    def __init__(self, client):
        self.client = client
        self.engine = SearchEngine()
        self.cache = CacheManager(client.db)

    async def get_cached(self, video_id):
        return await self.cache.get(video_id)

    async def prepare_song(self, video_id):

        result = await self.engine.download_song(video_id)

        if not result:
            return None

        if not result.get("success"):
            return None

        data = result["data"]

        filepath = data.get("filepath")

        if not filepath:
            return None

        if not os.path.exists(filepath):
            return None

        return {
            "title": data.get("title"),
            "uploader": data.get("uploader"),
            "duration": data.get("duration"),
            "filepath": filepath
        }

    async def upload_song(self, song):

    logger.info(f"⬆️ Uploading to storage: {song['title']}")

    msg = await self.client.send_audio(
        chat_id=STORAGE_CHAT_ID,
        audio=song["filepath"],
        title=song["title"],
        performer=song["uploader"],
        caption="🎵 Inline Cache"
    )

    if os.path.exists(song["filepath"]):
        try:
            os.remove(song["filepath"])
        except Exception:
            pass

    if not msg.audio:
        return None

    return msg.audio.file_id

    async def cache_song(
        self,
        video_id,
        file_id,
        song
    ):

        await self.cache.save(
            video_id=video_id,
            file_id=file_id,
            title=song["title"],
            duration=song["duration"],
            uploader=song["uploader"]
        )

        return file_id

    async def get_or_create(self, video_id):

    cached = await self.cache.get(video_id)

    if cached:
        logger.info(f"⚡ Cache Hit: {video_id}")
        return cached

    logger.info(f"⬇️ Cache Miss: {video_id}")

    song = await self.prepare_song(video_id)

    if not song:
        return None

    file_id = await self.upload_song(song)

    if not file_id:
        return None

    await self.cache.save(
        video_id=video_id,
        file_id=file_id,
        title=song["title"],
        duration=song["duration"],
        uploader=song["uploader"]
    )

    return await self.cache.get(video_id)