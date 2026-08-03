import asyncio
import logging
import traceback

from pyrogram.types import (
    InlineQuery,
    InlineQueryResultCachedAudio,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
from api.cache import CacheManager

logger = logging.getLogger(__name__)

async def cached_result(song, cache):

    return InlineQueryResultCachedAudio(
        id=song["id"],
        audio_file_id=cache["file_id"],
        caption=f"🎵 {song['title']}",
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
async def loading_result(song):

    return InlineQueryResultArticle(
        id=f"loading_{song['id']}",
        title=song["title"],
        description="Preparing music...",
        input_message_content=InputTextMessageContent(
            "⏳ Preparing music..."
        )
    )
@Bot.on_inline_query()
async def inline_query(client, inline_query):

    query = inline_query.query.strip()

    if not query:
        return

    engine = SearchEngine()

    cache = CacheManager(client.db)

    response = await engine.search(query)

    results = []

    for song in response["results"]:

        cached = await cache.get(song["id"])

        if cached:

            results.append(
                await cached_result(song, cached)
            )

        else:

            results.append(
                await loading_result(song)
            )

    await inline_query.answer(
        results,
        cache_time=5,
        is_personal=True,
    )
