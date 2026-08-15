import asyncio
import logging
import uuid

from pyrogram import enums
from pyrogram.types import (
    InlineQueryResultCachedAudio,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from jiosaavn.bot import Bot
from jiosaavn.emojis import *
from api.search_engine import SearchEngine
from api.inline_helper import InlineHelper

logger = logging.getLogger(__name__)


def inline_audio_markup(video_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "ᴀᴅᴅ ᴛᴏ ꜰᴀᴠᴏʀɪᴛᴇꜱ",
                callback_data=f"fav_add_{video_id}",
                style=enums.ButtonStyle.DANGER,
                icon_custom_emoji_id="5255861796350224063"
            )
        ],
        [
            InlineKeyboardButton(
                "ꜱᴇᴀʀᴄʜ ᴀɢᴀɪɴ",
                switch_inline_query_current_chat="",
                style=enums.ButtonStyle.PRIMARY,
                icon_custom_emoji_id="6318752565865482087"
            )
        ],
        [
            InlineKeyboardButton(
                "ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                url="https://t.me/AartiMusic_bot?startgroup=true",
                style=enums.ButtonStyle.SUCCESS,
                icon_custom_emoji_id="5861735798956627072"
            )
        ]
    ])


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
            caption=f"{E_TRACK} **{cache['title']}**\n\n__{E_SPARKLE} ᴠɪᴀ ᴀᴀʀᴛɪᴍᴜꜱɪᴄ__",
            reply_markup=inline_audio_markup(song["id"])
        )

    return InlineQueryResultArticle(
        id=f"dl_{song['id']}",
        title=song["title"][:60],
        description=f"{song.get('uploader', 'Unknown')[:60]}",
        thumb_url=thumbnail_url,
        input_message_content=InputTextMessageContent(
            f"{E_DOWNLOAD} **ꜰᴇᴛᴄʜɪɴɢ…**\n\n>{song['title']}"
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "ʟᴏᴀᴅɪɴɢ…",
                callback_data="loading",
                style=enums.ButtonStyle.PRIMARY
            )
        ]])
    )


@Bot.on_inline_query()
async def inline_query(client, inline_query):
    query = inline_query.query.strip()

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
                title="ᴀᴀʀᴛɪ ᴍᴜꜱɪᴄ",
                thumb_url="https://raw.githubusercontent.com/makwanaj789-sys/Umclon-reset-file/main/thumb.jpg",
                description="Type a song name — I'll find it for you",
                input_message_content=InputTextMessageContent(
                    f"{E_SEARCH} **ᴀᴀʀᴛɪ ᴍᴜꜱɪᴄ**\n\n"
                    f">Type `@AartiMusic_bot` followed by\n"
                    f">any song name to search."
                ),
            )
        ]
        await inline_query.answer(results=results, cache_time=1, is_personal=True)
        return

    logger.info(f"📥 INLINE QUERY: '{query}' from user {inline_query.from_user.id}")

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

    await inline_query.answer(results=results, cache_time=0, is_personal=True)
    logger.info(f"✅ ANSWERED query '{query}' with {len(results)} results")