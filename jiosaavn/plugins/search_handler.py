import logging
import asyncio

from api.search_engine import SearchEngine
from jiosaavn.bot import Bot
from jiosaavn.emojis import *

from pyrogram import filters, enums
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

    # STATS: track user and group
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
        # Extract query
        if message.chat.type == ChatType.PRIVATE:
            query = message.text.strip()
        else:
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                return await message.reply(
                    f"**◈ ᴍɪꜱꜱɪɴɢ ᴛʀᴀᴄᴋ ɴᴀᴍᴇ ◈**\n\n"
                    f">{E_WRITE} Tell me what to look for.\n"
                    f">Example: `/am Alan Walker Faded`"
                )
            query = parts[1].strip()
            if not query:
                return await message.reply(
                    f"**◈ ᴍɪꜱꜱɪɴɢ ᴛʀᴀᴄᴋ ɴᴀᴍᴇ ◈**\n\n"
                    f">{E_WRITE} Tell me what to look for."
                )

        # Magnifier only — no text
        send_msg = await message.reply(E_SEARCH, quote=True)

        engine = SearchEngine()
        response = await engine.search(query)

        if not response or not isinstance(response, dict):
            return await send_msg.edit(
                f"**◈ ɴᴏ ʀᴇꜱᴜʟᴛꜱ ◈**\n\n"
                f">{E_STOP} Nothing found for `{query}`"
            )

        results = response.get("results", [])
        if not results:
            return await send_msg.edit(
                f"**◈ ɴᴏ ʀᴇꜱᴜʟᴛꜱ ◈**\n\n"
                f">{E_STOP} Nothing found for `{query}`"
            )

        # STATS: search count
        try:
            await client.db.add_search(
                user_id=message.from_user.id,
                chat_id=message.chat.id
            )
        except Exception:
            logger.exception("Search tracking error")

        # Build result buttons
        buttons = []
        for result in results:
            title = result.get("title", "Unknown")
            artist = result.get("uploader", "Unknown Artist")
            duration = result.get("duration", 0)
            dur_str = f"{duration//60}:{duration%60:02d}" if duration else "N/A"
            video_id = result.get("id")

            if video_id:
                btn_text = f"{title} — {artist} ({dur_str})"
                buttons.append([
                    InlineKeyboardButton(
                        btn_text[:60],
                        callback_data=f"youtube#{video_id}",
                        style=enums.ButtonStyle.PRIMARY,
                        icon_custom_emoji_id="5911274703367968100"
                    )
                ])

        if not buttons:
            return await send_msg.edit(
                f"**◈ ɴᴏ ʀᴇꜱᴜʟᴛꜱ ◈**\n\n"
                f">{E_STOP} Nothing found for `{query}`"
            )

        buttons.append([
            InlineKeyboardButton(
                "ᴄʟᴏꜱᴇ",
                callback_data="close",
                style=enums.ButtonStyle.DANGER,
                icon_custom_emoji_id="5974083768233760323"
            )
        ])

        await send_msg.edit(
            f"**◈ ꜱᴇᴀʀᴄʜ ʀᴇꜱᴜʟᴛꜱ ◈**\n\n"
            f">{E_SEARCH} **{query}**\n"
            f">{E_CASSETTE} Found `{len(buttons) - 1}` tracks\n\n"
            f"__{E_SPARKLE} Tap any track to download__",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.exception("Search Handler Error")
        if send_msg:
            await send_msg.edit(f"**◈ ᴇʀʀᴏʀ ◈**\n\n>`{e}`")