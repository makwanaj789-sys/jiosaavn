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
from api.inline_helper import InlineHelper

logger = logging.getLogger(__name__)

async def cached_result(song, cache):

    return InlineQueryResultCachedAudio(
        id=f"cached_{song['id']}",
        audio_file_id=cache["file_id"],
        caption=f"🎵 {cache['title']}",
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
async def build_result(helper, song):
    try:
        cache = await helper.get_cached(song["id"])
    except Exception:
        cache = None

    if cache:
        return InlineQueryResultCachedAudio(
            id=f"cached_{song['id']}",
            audio_file_id=cache["file_id"],
            caption=f"🎵 {cache['title']}",
        )

    # Non-cached -> placeholder, chosen_inline_result handler baad me download karega
    return InlineQueryResultArticle(
        id=f"dl_{song['id']}",
        title=song["title"],
        description="Tap to download",
        input_message_content=InputTextMessageContent(
            f"🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨: {song['title']}..."
        )
    )

    return InlineQueryResultCachedAudio(
        id=f"cached_{song['id']}",
        audio_file_id=cache["file_id"],
        caption=f"🎵 {cache['title']}",
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
@Bot.on_inline_query()
async def inline_query(client, inline_query):

    query = inline_query.query.strip()

    if not query:
        return

    engine = SearchEngine()
    helper = InlineHelper(client)

    response = await engine.search(query)

    if not response.get("results"):
        await inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True
        )
        return

    tasks = []

    for song in response["results"]:
        tasks.append(
            build_result(
                helper,
                song
            )
        )

    results = await asyncio.gather(
        *tasks,
        return_exceptions=False
    )

    await inline_query.answer(
        results=results,
        cache_time=5,
        is_personal=True,
    )
