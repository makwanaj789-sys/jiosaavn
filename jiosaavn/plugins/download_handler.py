import logging
import traceback
from pyrogram import ContinuePropagation
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from jiosaavn.bot import Bot
from api.inline_helper import InlineHelper
from api.favorites import FavoritesManager

logger = logging.getLogger(__name__)


@Bot.on_callback_query()
async def download_callback(client: Bot, callback: CallbackQuery):
    try:
        data = callback.data

        if not data.startswith("youtube#"):
            raise ContinuePropagation   # 🔥 FIX: baaki handlers ko chance do

        if not callback.message:
            await callback.answer(
                "⚠️ Please search again using inline mode (@yourbot query).",
                show_alert=True
            )
            return

        await callback.answer()

        video_id = data.split("#")[1]
        if not video_id:
            await callback.message.edit_text("❌ Invalid video ID.")
            return

        status_msg = callback.message
        await status_msg.edit_text("🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨 𝘺𝘰𝘶𝘳 𝘵𝘳𝘢𝘤𝘬...")

        helper = InlineHelper(client)
        song = await helper.get_or_create(video_id)

        if not song:
            await status_msg.edit_text("❌ Download failed.")
            return

        await status_msg.edit_text(f"⚡ 𝘍𝘪𝘯𝘪𝘴𝘩𝘪𝘯𝘨 𝘶𝘱... `{song['title']}`...")

        favorites = FavoritesManager(client.db)
        is_fav = await favorites.is_favorite(callback.from_user.id, video_id)

        await client.send_audio(
            chat_id=callback.message.chat.id,
            audio=song["file_id"],
            title=song["title"],
            performer=song.get("uploader", "YouTube"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "💔 Remove Favorite" if is_fav else "❤️ Add to Favorites",
                    callback_data=f"fav_remove_{video_id}" if is_fav else f"fav_add_{video_id}"
                )],
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")],
                [InlineKeyboardButton("➕ Add me to your group", url="https://t.me/AartiMusic_bot?startgroup=true")]
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