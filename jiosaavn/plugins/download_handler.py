import logging
import traceback
from pyrogram import ContinuePropagation, enums
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from jiosaavn.bot import Bot
from jiosaavn.emojis import *
from api.inline_helper import InlineHelper
from api.favorites import FavoritesManager

logger = logging.getLogger(__name__)


@Bot.on_callback_query()
async def download_callback(client: Bot, callback: CallbackQuery):
    try:
        data = callback.data

        if not data.startswith("youtube#"):
            raise ContinuePropagation   # let other handlers run

        if not callback.message:
            await callback.answer(
                "⚠️ Please search again using inline mode (@AartiMusic_bot query).",
                show_alert=True
            )
            return

        await callback.answer()

        video_id = data.split("#")[1]
        if not video_id:
            await callback.message.edit_text(
                f"**◈ ɪɴᴠᴀʟɪᴅ ᴛʀᴀᴄᴋ ◈**\n\n>{E_STOP} Couldn't read that video ID."
            )
            return

        status_msg = callback.message
        await status_msg.edit_text(f"{E_DOWNLOAD} **ꜰᴇᴛᴄʜɪɴɢ ʏᴏᴜʀ ᴛʀᴀᴄᴋ…**")

        helper = InlineHelper(client)
        song = await helper.get_or_create(video_id)

        if not song:
            await status_msg.edit_text(
                f"**◈ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ ◈**\n\n"
                f">{E_STOP} Couldn't fetch that track."
            )
            return

        await status_msg.edit_text(
            f"{E_SPARKLE} **ꜰɪɴɪꜱʜɪɴɢ ᴜᴘ…**\n\n>{E_TRACK} `{song['title']}`"
        )

        favorites = FavoritesManager(client.db)
        is_fav = await favorites.is_favorite(callback.from_user.id, video_id)

        await client.send_audio(
            chat_id=callback.message.chat.id,
            audio=song["file_id"],
            title=song["title"],
            performer=song.get("uploader", "YouTube"),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "ʀᴇᴍᴏᴠᴇ ꜰᴀᴠᴏʀɪᴛᴇ" if is_fav else "ᴀᴅᴅ ᴛᴏ ꜰᴀᴠᴏʀɪᴛᴇꜱ",
                        callback_data=f"fav_remove_{video_id}" if is_fav else f"fav_add_{video_id}",
                        style=enums.ButtonStyle.DANGER,
                        icon_custom_emoji_id="5255861796350224063"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "ꜱᴇᴀʀᴄʜ ᴀɢᴀɪɴ",
                        switch_inline_query_current_chat="",
                        style=enums.ButtonStyle.PRIMARY,
                        icon_custom_emoji_id="6318752565865482087"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                        url="https://t.me/AartiMusic_bot?startgroup=true",
                        style=enums.ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="5861735798956627072"
                    )
                ]
            ])
        )

        await status_msg.delete()

        logger.info(f"✅ SONG SENT SUCCESSFULLY: {song['title']}")

    except ContinuePropagation:
        raise
    except Exception as e:
        logger.error(f"❌ DOWNLOAD ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await callback.answer("❌ Download failed!", show_alert=True)
        except Exception:
            pass