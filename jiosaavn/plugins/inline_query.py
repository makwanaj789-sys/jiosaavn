import asyncio
import logging
import os
import re
import traceback

from pyrogram.types import (
    InlineQuery,
    InlineQueryResultCachedAudio,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from pyrogram.enums import ParseMode

from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
from api.cache import CacheManager

logger = logging.getLogger(__name__)

async def build_cached_result(song, cache_data):
    duration = song.get("duration", 0)

    return InlineQueryResultCachedAudio(
        id=f"cache_{song['id']}",
        audio_file_id=cache_data["file_id"],
        caption=(
            f"🎵 {song['title']}\n"
            f"👤 {song['uploader']}\n"
            f"⏱ {duration//60}:{duration%60:02d}"
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔍 Search Again",
                        switch_inline_query_current_chat=""
                    )
                ]
            ]
        )
    )
async def build_download_result(song):
    duration = song.get("duration", 0)

    return InlineQueryResultArticle(
        id=f"download_{song['id']}",
        title=song["title"],
        description=f"{song['uploader']} • {duration//60}:{duration%60:02d}",
        input_message_content=InputTextMessageContent(
            "⏳ Preparing music..."
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬇ Download",
                        callback_data=f"download_{song['id']}"
                    )
                ]
            ]
        )
    )
engine = SearchEngine()
cache = CacheManager(client.db)

response = await engine.search(query)

results = []

for song in response.get("results", []):

    cached = await cache.get(song["id"])

    if cached:
        results.append(
            await build_cached_result(song, cached)
        )
    else:
        results.append(
            await build_download_result(song)
        )

await inline_query.answer(
    results,
    cache_time=5,
    is_personal=True
)
