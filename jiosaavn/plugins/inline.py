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
            
            for result in search_results:
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
                    # 🔥 FIX: Download handler ke callback data ke saath
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
                            # 🔥 Callback data jo download_handler trigger karega
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton(
                                    "📥 Download",
                                    callback_data=f"youtube#{video_id}"  # 🔥 Same as normal search
                                )],
                                [InlineKeyboardButton(
                                    "🔄 Search Again",
                                    switch_inline_query_current_chat=""
                                )]
                            ]),
                            id=video_id
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