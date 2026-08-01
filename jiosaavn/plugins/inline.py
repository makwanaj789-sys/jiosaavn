from pyrogram import filters
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent
)

from jiosaavn.bot import Bot
from api.search_engine import SearchEngine


@Bot.on_inline_query()
async def inline_search(client, inline_query: InlineQuery):
    query = inline_query.query.strip()

    if not query:
        return

    engine = SearchEngine()
    response = await engine.search(
        query=query,
        search_type="songs",
        page_size=10
    )

    results = []

    for item in response.get("results", []):
        title = item.get("title", "Unknown")
        artist = item.get("artist", "Unknown")
        video_id = item.get("id")

        results.append(
            InlineQueryResultArticle(
                title=title,
                description=artist,
                input_message_content=InputTextMessageContent(
                    f"🎵 **{title}**\n👤 {artist}\n\n⏳ Downloading..."
                ),
                reply_markup=None,
                id=video_id
            )
        )

    await inline_query.answer(
        results,
        cache_time=1,
        is_personal=True
    )