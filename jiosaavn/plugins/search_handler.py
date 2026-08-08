import logging
import traceback
import asyncio

from api.search_engine import SearchEngine
from jiosaavn.bot import Bot

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

logger = logging.getLogger(__name__)

private_search_filter = (filters.text & filters.incoming & filters.private)
group_search_filter = (filters.command("am") & filters.incoming)

@Bot.on_message(private_search_filter | group_search_filter)
async def search(client: Bot, message: Message):
    if message.via_bot:
       return

    # 🔥 STATS: user aur group track karo
    if message.from_user:
        try:
            exists = await client.db.is_user_exist(message.from_user.id)
            if not exists:
                await client.db.add_user(message.from_user.id)
        except Exception:
            logger.exception("User tracking error")

    if message.chat.type != ChatType.PRIVATE:
        try:
            await client.db.add_group(message.chat.id)
        except Exception:
            logger.exception("Group tracking error")

    send_msg = None
    try:
        # Query extract karo
        if message.chat.type == ChatType.PRIVATE:
            query = message.text.strip()
        else:
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                return await message.reply("❌ Please enter a song name.\nExample: `/am Alan Walker`")
            query = parts[1].strip()
            if not query:
                return await message.reply("❌ Please enter a song name.")

        send_msg = await message.reply("__**Searching YouTube... ⏳**__", quote=True)

        # Search karo - Same method inline mein bhi use hogi
        engine = SearchEngine()
        response = await engine.search(query)

        if not response or not isinstance(response, dict):
            return await send_msg.edit(f"🔎 No results found for `{query}`")

        results = response.get("results", [])
        if not results:
            return await send_msg.edit(f"🔎 No results found for `{query}`")

        # 🔥 STATS: search count badhao
        try:
            await client.db.add_search(
                user_id=message.from_user.id,
                chat_id=message.chat.id
            )
        except Exception:
            logger.exception("Search tracking error")

        # Buttons banao
        buttons = []
        for result in results:
            title = result.get("title", "Unknown")
            artist = result.get("uploader", "Unknown Artist")
            duration = result.get("duration", 0)
            dur_str = f"{duration//60}:{duration%60:02d}" if duration else "N/A"
            video_id = result.get("id")

            if video_id:
                btn_text = f"🎙 {title} - {artist} ({dur_str})"
                buttons.append([InlineKeyboardButton(btn_text, callback_data=f"youtube#{video_id}")])

        if not buttons:
            return await send_msg.edit(f"🔎 No results found for `{query}`")

        buttons.append([InlineKeyboardButton("Close ❌", callback_data="close")])

        await send_msg.edit(
            f"**🔍 Search Query:** `{query}`\n\n**📜 Results:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.exception("Search Handler Error")
        if send_msg:
            await send_msg.edit(f"❌ Error: {e}")