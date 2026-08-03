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

    cache = await helper.get_or_create(song["id"])

    if cache:

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

    return InlineQueryResultArticle(
        id=f"error_{song['id']}",
        title=song["title"],
        description="Unable to prepare this song.",
        input_message_content=InputTextMessageContent(
            "❌ Failed to prepare audio."
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

    results = []

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
        results=results
        cache_time=5,
        is_personal=True,
    )
