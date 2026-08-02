# jiosaavn/plugins/inline_query.py

import os
import re
import logging
import tempfile
import asyncio
from pyrogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
    InlineQueryResultAudio,
    InlineQueryResultCachedAudio,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.enums import ParseMode
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
from api.cache import CacheManager


logger = logging.getLogger(__name__)

@Bot.on_inline_query()
async def inline_query(client: Bot, inline_query: InlineQuery):
    """
    Handle inline queries - @musi style
    """
    try:
        query = inline_query.query.strip()
        
        # Agar query empty hai toh search prompt dikhao
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
                            [InlineKeyboardButton(
                                "🎵 Search Now",
                                switch_inline_query_current_chat=""
                            )]
                        ])
                    )
                ],
                cache_time=60,
                is_personal=True
            )
            return
        
        logger.info(f"🔍 INLINE SEARCH: {query} (User: {inline_query.from_user.id})")
        
        # ==========================================
        # SEARCH SONGS
        # ==========================================
        engine = SearchEngine()
        search_results = await engine.search(query, page_size=10)
        
        if not search_results or not search_results.get("results"):
            # No results found
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        id="no_results",
                        title="❌ No results found",
                        description=f"Couldn't find: {query}",
                        input_message_content=InputTextMessageContent(
                            f"❌ No results found for: {query}\n\nTry a different search term."
                        )
                    )
                ],
                cache_time=60,
                is_personal=True
            )
            return
        
        # ==========================================
        # CREATE INLINE RESULTS
        # ==========================================
        results = []
        cache = CacheManager(client.db)
        
        for idx, song in enumerate(search_results["results"][:10]):
            video_id = song.get("id")
            title = song.get("title", "Unknown")
            artist = song.get("uploader", "Unknown Artist")
            duration = song.get("duration", 0)
            
            # Check if song is cached
            cached = await cache.get(video_id)
            
            if cached and cached.get("file_id"):
                # 🔥 USE CACHED AUDIO (Direct send, no download)
                result = InlineQueryResultCachedAudio(
                    id=f"cached_{video_id}",
                    audio_file_id=cached["file_id"],
                    caption=f"🎵 **{title}**\n\n👤 **Artist:** {artist}\n⏱️ **Duration:** {duration//60}:{duration%60:02d}\n📦 **Source:** Cache",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "🎵 Search Again",
                            switch_inline_query_current_chat=""
                        )],
                        [InlineKeyboardButton(
                            "🤖 𝐀м𝓊ᔕ𝕀¢",
                            url="https://t.me/aartimusic_bot?start=home"
                        )]
                    ])
                )
                logger.info(f"⚡ CACHE RESULT: {title}")
            else:
                # 🔥 NEED TO DOWNLOAD - Show processing message
                result = InlineQueryResultArticle(
                    id=f"download_{video_id}",
                    title=f"🎵 {title}",
                    description=f"👤 {artist} | ⏱️ {duration//60}:{duration%60:02d}",
                    input_message_content=InputTextMessageContent(
                        f"⏳ **Downloading:** {title}\n\n"
                        f"👤 **Artist:** {artist}\n"
                        f"⏱️ **Duration:** {duration//60}:{duration%60:02d}\n\n"
                        f"_Please wait, this may take a few seconds..._",
                        parse_mode=ParseMode.MARKDOWN
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "⏳ Processing...",
                            callback_data=f"download_{video_id}"
                        )]
                    ])
                )
                logger.info(f"📥 DOWNLOAD REQUIRED: {title}")
            
            results.append(result)
        
        # ==========================================
        # ANSWER INLINE QUERY
        # ==========================================
        await inline_query.answer(
            results=results,
            cache_time=30,  # 30 seconds cache for inline results
            is_personal=True,
            switch_pm_text="🎵 Made with ❤️ by AartiMusic",
            switch_pm_parameter="start"
        )
        
        logger.info(f"✅ INLINE RESULTS SENT: {len(results)} results")
        
    except Exception as e:
        logger.error(f"❌ INLINE QUERY ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        id="error",
                        title="❌ Error",
                        description="Something went wrong!",
                        input_message_content=InputTextMessageContent(
                            f"❌ Error: {str(e)}"
                        )
                    )
                ],
                cache_time=0
            )
        except:
            pass