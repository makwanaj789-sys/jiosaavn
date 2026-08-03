# jiosaavn/plugins/inline_query.py

import os
import re
import logging
import traceback
from pyrogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
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

# 🔥 DEBUG: Check if file is loading
print("=" * 50)
print("📦 INLINE_QUERY.PY LOADED ✅")
print("=" * 50)
logger.info("📦 INLINE_QUERY.PY LOADED")

@Bot.on_inline_query()
async def inline_query(client: Bot, inline_query: InlineQuery):
    """
    Handle inline queries - @musi style
    """
    # 🔥 DEBUG: Check if function is called
    print("🔥 INLINE QUERY TRIGGERED!")
    logger.info("🔥 INLINE QUERY TRIGGERED!")
    
    try:
        query = inline_query.query.strip()
        user_id = inline_query.from_user.id
        
        # 🔥 DEBUG: Log everything
        print(f"📝 USER: {user_id}, QUERY: '{query}'")
        logger.info(f"📝 USER: {user_id}, QUERY: '{query}'")
        
        # Agar query empty hai toh search prompt dikhao
        if not query:
            print("⚠️ EMPTY QUERY - Showing prompt")
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
            print("✅ EMPTY QUERY RESPONSE SENT")
            return
        
        # ==========================================
        # SEARCH SONGS
        # ==========================================
        print(f"🔍 SEARCHING FOR: {query}")
        engine = SearchEngine()
        search_results = await engine.search(query, page_size=10)
        
        print(f"📊 SEARCH RESULTS: {len(search_results.get('results', []))} found")
        
        if not search_results or not search_results.get("results"):
            print("❌ NO RESULTS FOUND")
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
            
            # Format duration
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            # Check if song is cached
            cached = await cache.get(video_id)
            
            print(f"🎵 {idx+1}. {title} - {'CACHED ✅' if cached else 'NEED DOWNLOAD 📥'}")
            
            if cached and cached.get("file_id"):
                result = InlineQueryResultCachedAudio(
                    id=f"cached_{video_id}",
                    audio_file_id=cached["file_id"],
                    caption=f"🎵 **{title}**\n\n👤 **Artist:** {artist}\n⏱️ **Duration:** {duration_str}\n📦 **Source:** Cache",
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
            else:
                result = InlineQueryResultArticle(
                    id=f"download_{video_id}",
                    title=f"🎵 {title}",
                    description=f"👤 {artist} | ⏱️ {duration_str}",
                    input_message_content=InputTextMessageContent(
                        f"⏳ **Downloading:** {title}\n\n"
                        f"👤 **Artist:** {artist}\n"
                        f"⏱️ **Duration:** {duration_str}\n\n"
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
            
            results.append(result)
        
        # ==========================================
        # ANSWER INLINE QUERY
        # ==========================================
        print(f"📤 ANSWERING WITH {len(results)} RESULTS")
        await inline_query.answer(
            results=results,
            cache_time=30,
            is_personal=True,
            switch_pm_text="🎵 Made with ❤️ by AartiMusic",
            switch_pm_parameter="start"
        )
        
        print("✅ INLINE QUERY ANSWERED SUCCESSFULLY")
        logger.info(f"✅ INLINE RESULTS SENT: {len(results)} results")
        
    except Exception as e:
        print(f"❌ INLINE QUERY ERROR: {e}")
        print(traceback.format_exc())
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