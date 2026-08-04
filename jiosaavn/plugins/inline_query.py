import asyncio
import logging

from pyrogram.types import (
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
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Search Again", switch_inline_query_current_chat="")
            ]])
        )

    # Non-cached -> placeholder; reply_markup ZAROORI hai taaki inline_message_id mile
    return InlineQueryResultArticle(
        id=f"dl_{song['id']}",
        title=f"🎵 {song['title'][:60]}",
        description=f"👤 {song.get('uploader', 'Unknown')[:60]}",
        input_message_content=InputTextMessageContent(
            f"🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨: {song['title']}..."
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⏳ Loading...", callback_data="loading")
        ]])
    )

@Bot.on_inline_query()
async def inline_query(client, inline_query):
    query = inline_query.query.strip()

    if not query:
        return

    logger.info(f"📥 INLINE QUERY RECEIVED: '{query}' from user {inline_query.from_user.id}")

    engine = SearchEngine()
    helper = InlineHelper(client)

    response = await engine.search(query)

    if not response.get("results"):
        await inline_query.answer(results=[], cache_time=1, is_personal=True)
        return

    tasks = [build_result(helper, song) for song in response["results"]]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # 🔥 Debug: confirm reply_markup present hai results mein
    for r in results:
        has_markup = r.reply_markup is not None
        logger.info(f"📤 Result id={r.id} has_reply_markup={has_markup}")

    await inline_query.answer(results=results, cache_time=0, is_personal=True)
    logger.info(f"✅ ANSWERED query '{query}' with {len(results)} results")
