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
    # 🔥 LOG 1: Inline query receive hui
    logger.info(f"🔍 INLINE QUERY RECEIVED: {inline_query.query}")
    logger.info(f"👤 FROM USER: {inline_query.from_user.id}")
    logger.info(f"📝 QUERY LENGTH: {len(inline_query.query)}")
    
    query = inline_query.query.strip()
    
    if not query:
        logger.warning("⚠️ EMPTY QUERY - Returning empty results")
        return await inline_query.answer(
            [],
            cache_time=1,
            is_personal=True
        )

    try:
        logger.info(f"🔎 SEARCHING FOR: {query}")
        
        engine = SearchEngine()
        response = await engine.search(query)
        
        # 🔥 LOG 2: Search response
        logger.info(f"📊 SEARCH RESPONSE TYPE: {type(response)}")
        if response:
            logger.info(f"📊 RESULTS COUNT: {len(response.get('results', []))}")
        else:
            logger.warning("⚠️ RESPONSE IS NONE OR EMPTY")
        
        results = []
        
        if not response or not response.get("results"):
            logger.warning(f"⚠️ NO RESULTS FOR: {query}")
            # No results result
            results.append(
                InlineQueryResultArticle(
                    title="🔎 No Results Found",
                    description=f"No songs found for: {query}",
                    input_message_content=InputTextMessageContent(
                        f"🔎 No results found for `{query}`\n\n💡 Try different keywords."
                    ),
                    id="no_results",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Try Again", switch_inline_query_current_chat=query)]
                    ])
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
                
                # Duration format
                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    dur_str = f"{minutes}:{seconds:02d}"
                else:
                    dur_str = "N/A"
                
                logger.info(f"  {idx+1}. {title} - {artist} (ID: {video_id})")
                
                if video_id:
                    results.append(
                        InlineQueryResultArticle(
                            title=f"🎵 {title[:64]}",
                            description=f"👤 {artist[:64]} ⏱ {dur_str}",
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
                            id=video_id
                        )
                    )
        
        # 🔥 LOG 3: Results count
        logger.info(f"📤 SENDING {len(results)} RESULTS TO USER")
        
        await inline_query.answer(
            results,
            cache_time=30,
            is_personal=True,
            switch_pm_text="🔍 Search Music",
            switch_pm_parameter="search"
        )
        
        logger.info("✅ INLINE QUERY ANSWERED SUCCESSFULLY")

    except Exception as e:
        logger.error(f"❌ INLINE SEARCH ERROR: {e}")
        logger.error(traceback.format_exc())
        
        try:
            await inline_query.answer(
                [
                    InlineQueryResultArticle(
                        title="❌ Error",
                        description=f"Error: {str(e)[:50]}",
                        input_message_content=InputTextMessageContent(
                            f"❌ **Error Occurred**\n\n`{str(e)}`\n\nPlease try again later."
                        ),
                        id="error",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Retry", switch_inline_query_current_chat=query)]
                        ])
                    )
                ],
                cache_time=1,
                is_personal=True
            )
        except Exception as e2:
            logger.error(f"❌ FAILED TO ANSWER: {e2}")