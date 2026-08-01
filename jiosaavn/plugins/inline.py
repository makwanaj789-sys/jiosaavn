from pyrogram import filters
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
        # Search engine ko call karo
        engine = SearchEngine()
        response = await engine.search(
            query=query,
            search_type="songs",
            page_size=10  # 10 results tak
        )

        results = []
        
        # Agar response nahi hai ya results nahi hai
        if not response or not response.get("results"):
            # No results message dikhao
            results.append(
                InlineQueryResultArticle(
                    title="🔎 No Results Found",
                    description=f"No songs found for: {query}",
                    input_message_content=InputTextMessageContent(
                        f"🔎 No results found for `{query}`\n\nTry different keywords or check spelling."
                    ),
                    id="no_results",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Try Again", switch_inline_query_current_chat=query)]
                    ])
                )
            )
        else:
            # Results ko format karo
            for item in response.get("results", []):
                title = item.get("title", "Unknown Title")
                artist = item.get("uploader", "Unknown Artist")
                video_id = item.get("id")
                duration = item.get("duration", 0)
                
                # Duration ko format karo
                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    dur_str = f"{minutes}:{seconds:02d}"
                else:
                    dur_str = "N/A"
                
                # Title aur artist ko truncate karo (Telegram limit 64 chars)
                display_title = title[:64] if len(title) > 64 else title
                display_artist = artist[:64] if len(artist) > 64 else artist
                
                if video_id:
                    results.append(
                        InlineQueryResultArticle(
                            title=display_title,
                            description=f"🎤 {display_artist} ⏱ {dur_str}",
                            input_message_content=InputTextMessageContent(
                                f"🎵 **{title}**\n"
                                f"👤 **Artist:** {artist}\n"
                                f"⏱ **Duration:** {dur_str}\n\n"
                                f"⬇️ Downloading your song... Please wait."
                            ),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("⏳ Downloading...", callback_data="downloading")],
                                [InlineKeyboardButton("🔄 Search Again", switch_inline_query_current_chat="")]
                            ]),
                            id=video_id,
                            thumb_url="https://img.icons8.com/color/48/000000/youtube-music.png"  # Optional thumbnail
                        )
                    )
            
            # Agar kuch results nahi bane (kuch gadbad hui)
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
            cache_time=30,  # 30 seconds cache for better performance
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
                        id="error"
                    )
                ],
                cache_time=1,
                is_personal=True
            )
        except Exception as e2:
            logger.error(f"Failed to answer inline query: {e2}")