import asyncio
import logging
import uuid

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

    thumbnail_url = f"https://i.ytimg.com/vi/{song['id']}/hqdefault.jpg"

    if cache:
        return InlineQueryResultCachedAudio(
            id=f"cached_{song['id']}",
            audio_file_id=cache["file_id"],
            caption=f"🎵 {cache['title']}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Search Again", switch_inline_query_current_chat="")
            ],
                [InlineKeyboardButton("➕ Add me to your group", url="https://t.me/AartiMusic_bot?startgroup=true")]
])
        )

    return InlineQueryResultArticle(
        id=f"dl_{song['id']}",
        title=f"🎵 {song['title'][:60]}",
        description=f"👤 {song.get('uploader', 'Unknown')[:60]}",
        thumb_url=thumbnail_url,
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

    # 🔥 STATS: user track karo (empty query pe bhi, kyunki user ne bot open kiya)
    if inline_query.from_user:
        try:
            exists = await client.db.is_user_exist(inline_query.from_user.id)
            if not exists:
                await client.db.add_user(inline_query.from_user.id)
        except Exception:
            logger.exception("User tracking error")

    if not query:
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="AMusic 🎵",
                thumb_url="https://raw.githubusercontent.com/makwanaj789-sys/Umclon-reset-file/main/thumb.jpg",
                description="🎧 Search any song, Aarti will find it...",
                input_message_content=InputTextMessageContent(
                    "🎵 AartiMusic se gaana search karo!"
                ),
            )
        ]
        await inline_query.answer(results=results, cache_time=1, is_personal=True)
        return

    logger.info(f"📥 INLINE QUERY RECEIVED: '{query}' from user {inline_query.from_user.id}")

    # 🔥 STATS: search count badhao
    try:
        await client.db.add_search(
            user_id=inline_query.from_user.id,
            chat_id=0
        )
    except Exception:
        logger.exception("Search tracking error")

    engine = SearchEngine()
    helper = InlineHelper(client)

    response = await engine.search(query)

    if not response.get("results"):
        await inline_query.answer(results=[], cache_time=1, is_personal=True)
        return

    tasks = [build_result(helper, song) for song in response["results"]]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    for r in results:
        has_markup = r.reply_markup is not None
        logger.info(f"📤 Result id={r.id} has_reply_markup={has_markup}")

    await inline_query.answer(results=results, cache_time=0, is_personal=True)
    logger.info(f"✅ ANSWERED query '{query}' with {len(results)} results")