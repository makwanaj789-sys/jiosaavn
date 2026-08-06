import logging
import traceback
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from jiosaavn.bot import Bot
from api.inline_helper import InlineHelper

logger = logging.getLogger(__name__)


@Bot.on_callback_query()
async def download_callback(client: Bot, callback: CallbackQuery):
    try:
        data = callback.data

        if not data.startswith("youtube#"):
            return

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

        # 🔥 FIX: ab cache check/save InlineHelper ke through hoga
        helper = InlineHelper(client)
        song = await helper.get_or_create(video_id)

        if not song:
            await status_msg.edit_text("❌ Download failed.")
            return

        await status_msg.edit_text(f"⚡ 𝘍𝘪𝘯𝘪𝘴𝘩𝘪𝘯𝘨 𝘶𝘱... `{song['title']}`...")

        await client.send_audio(
            chat_id=callback.message.chat.id,
            audio=song["file_id"],   # 🔥 file_id use ho raha hai, cache hit ho to instant
            title=song["title"],
            performer=song.get("uploader", "YouTube"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")],
                [InlineKeyboardButton("🤖 𝐀м𝓊ᔕ𝕀¢", url="https://t.me/aartimusic_bot?start=home")]
            ])
        )

        await status_msg.delete()

        logger.info(f"✅ SONG SENT SUCCESSFULLY: {song['title']}")

    except Exception as e:
        logger.error(f"❌ DOWNLOAD ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await callback.answer("❌ Download failed!", show_alert=True)
        except Exception:
            pass