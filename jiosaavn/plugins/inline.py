import logging
import traceback
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

@Bot.on_inline_query()
async def inline_search(client, inline_query: InlineQuery):
    logger.info(f"🔍 INLINE QUERY: {inline_query.query}")
    
    query = inline_query.query.strip()
    
    if not query:
        return await inline_query.answer(
            [],
            cache_time=1,
            is_personal=True
        )

    try:
        logger.info(f"🔎 SEARCHING: {query}")
        
        engine = SearchEngine()
        response = await engine.search(query)
        
        results = []
        
        if not response or not response.get("results"):
            results.append(
                InlineQueryResultArticle(
                    title="🔎 No Results Found",
                    description=f"No songs found for: {query}",
                    input_message_content=InputTextMessageContent(
                        f"🔎 No results found for `{query}`"
                    ),
                    id="no_results"
                )
            )
        else:
            search_results = response.get("results", [])
            logger.info(f"✅ FOUND {len(search_results)} RESULTS")
            
            for idx, result in enumerate(search_results):
                title = result.get("title", "Unknown")
                artist = result.get("uploader", "Unknown Artist")
                video_id = result.get("id")
                duration = result.get("duration", 0)
                
                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    dur_str = f"{minutes}:{seconds:02d}"
                else:
                    dur_str = "N/A"
                
                if video_id:
                    # 🔥 FIX: Unique ID banao
                    unique_id = f"yt_{video_id}_{idx}"
                    
                    results.append(
                        InlineQueryResultArticle(
                            title=f"🎵 {title[:60]}",
                            description=f"👤 {artist[:60]} ⏱ {dur_str}",
                            input_message_content=InputTextMessageContent(
                                f"**🎵 {title}**\n"
                                f"**👤 Artist:** {artist}\n"
                                f"**⏱ Duration:** {dur_str}\n\n"
                                f"⬇️ Click to download..."
                            ),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("⏳ Downloading...", callback_data=f"dl_{video_id}")],
                                [InlineKeyboardButton("🔄 Search Again", switch_inline_query_current_chat="")]
                            ]),
                            id=unique_id  # 🔥 Unique ID use karo
                        )
                    )
        
        logger.info(f"📤 SENDING {len(results)} RESULTS")
        
        await inline_query.answer(
            results,
            cache_time=10,
            is_personal=True
        )
        
        logger.info("✅ INLINE QUERY ANSWERED")

    except Exception as e:
        logger.error(f"❌ INLINE ERROR: {e}")
        logger.error(traceback.format_exc())
