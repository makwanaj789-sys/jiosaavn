from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
import logging

logger = logging.getLogger(__name__)

@Bot.on_inline_query()
async def inline_search(client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    
    # Agar query empty hai toh kuch mat dikhao
    if not query:
        return await inline_query.answer(
            [],
            cache_time=1,
            is_personal=True
        )

    try:
        # Search engine ko call karo - EXACTLY same as search handler
        engine = SearchEngine()
        response = await engine.search(query)  # Same as search handler

        results = []
        
        # Same logic as search handler
        if not response or not isinstance(response, dict):
            # No results - single result dikhao
            results.append(
                InlineQueryResultArticle(
                    title="🔎 No Results Found",
                    description=f"No songs found for: {query}",
                    input_message_content=InputTextMessageContent(
                        f"🔎 No results found for `{query}`\n\n"
                        f"💡 Try different keywords or check spelling."
                    ),
                    id="no_results",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Search Again", switch_inline_query_current_chat=query)]
                    ])
                )
            )
        else:
            search_results = response.get("results", [])
            
            if not search_results:
                # No results
                results.append(
                    InlineQueryResultArticle(
                        title="🔎 No Results Found",
                        description=f"No songs found for: {query}",
                        input_message_content=InputTextMessageContent(
                            f"🔎 No results found for `{query}`\n\n"
                            f"💡 Try different keywords or check spelling."
                        ),
                        id="no_results",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Search Again", switch_inline_query_current_chat=query)]
                        ])
                    )
                )
            else:
                # Results mil gaye - Same format as search handler
                for result in search_results:
                    title = result.get("title", "Unknown")
                    artist = result.get("uploader", "Unknown Artist")
                    video_id = result.get("id")
                    duration = result.get("duration", 0)
                    
                    # Duration format - same as search handler
                    if duration:
                        minutes = duration // 60
                        seconds = duration % 60
                        dur_str = f"{minutes}:{seconds:02d}"
                    else:
                        dur_str = "N/A"
                    
                    if video_id:
                        # Inline result create karo
                        results.append(
                            InlineQueryResultArticle(
                                title=f"🎵 {title[:64]}",  # Title limited to 64 chars
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
                                id=video_id,
                                thumb_url="https://img.icons8.com/color/48/000000/youtube-music.png"
                            )
                        )

        # Agar kuch results nahi bane toh error message dikhao
        if not results:
            results.append(
                InlineQueryResultArticle(
                    title="⚠️ Error",
                    description="Something went wrong",
                    input_message_content=InputTextMessageContent(
                        f"⚠️ Error searching for `{query}`\n\nPlease try again later."
                    ),
                    id="error"
                )
            )

        # Results ko answer karo
        await inline_query.answer(
            results,
            cache_time=30,
            is_personal=True,
            switch_pm_text="🔍 Search Music",
            switch_pm_parameter="search"
        )

    except Exception as e:
        logger.error(f"Inline Search Error: {e}")
        
        # Error result dikhao
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
            logger.error(f"Failed to answer inline query: {e2}")