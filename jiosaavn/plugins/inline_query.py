import os
import re
import logging
import traceback
import asyncio # IMPORTED FOR BACKGROUND TASKS
from pyrogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
    InlineQueryResultCachedAudio,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.enums import ParseMode
from pyrogram.errors import QueryIdInvalid
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
from api.cache import CacheManager

logger = logging.getLogger(__name__)

print("=" * 50)
print("📦 INLINE_QUERY.PY LOADED ✅")
print("=" * 50)

@Bot.on_inline_query()
async def inline_query(client: Bot, inline_query: InlineQuery):
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id

    # 1. Handle Empty Query
    if not query:
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="start",
                    title="🔍 Search for songs!",
                    description="Type a song name to search",
                    input_message_content=InputTextMessageContent(
                        "🎵 **Music Search**\n\nType a song name to search for music!"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎵 Search Now", switch_inline_query_current_chat="")]
                    ])
                )
            ],
            cache_time=60,
            is_personal=True
        )
        return

    # 2. NEW APPROACH: Answer with a "Processing" result immediately, 
    # but use a callback button to actually trigger the download!
    # This guarantees the InlineQuery never expires.
    
    await inline_query.answer(
        results=[
            InlineQueryResultArticle(
                id=f"processing_{user_id}",
                title="⏳ Processing your request...",
                description=f"Looking for: {query}",
                input_message_content=InputTextMessageContent(
                    f"🔍 **Searching for:** `{query}`\n\n"
                    f"⏳ Please be patient. I am fetching the songs right now.\n\n"
                    f"*If nothing appears in 10 seconds, click the button below:*"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔄 Force Search / Retry",
                        callback_data=f"force_search|{query}" # <-- This triggers the actual search
                    )]
                ])
            )
        ],
        cache_time=10,
        is_personal=True
    )