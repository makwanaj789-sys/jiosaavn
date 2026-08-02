import logging
import re
import os
import traceback
from pyrogram.types import (
    Message, 
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram import filters
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

@Bot.on_callback_query(filters=None)
async def download_callback(client: Bot, callback: CallbackQuery):
    try:
        await callback.answer()
        data = callback.data

        # 🔥 SIRF YOUTUBE CALLBACKS HANDLE KARO
        if not data.startswith("youtube#"): 
            return

        video_id = data.split("#")[1]
        if not video_id:
            if callback.message:
                await callback.message.edit_text("❌ Invalid video ID.")
            else:
                await callback.answer("❌ Invalid video ID.", show_alert=True)
            return

        # 🔥 Status message handle karo
        status_msg = None
        if callback.message:
            status_msg = callback.message
            await status_msg.edit_text("🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨 𝘺𝘰𝘶𝘳 𝘵𝘳𝘢𝘤𝘬...")
        else:
            status_msg = await client.send_message(
                chat_id=callback.from_user.id,
                text="🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨 𝘺𝘰𝘶𝘳 𝘵𝘳𝘢𝘤𝘬..."
            )

        engine = SearchEngine()
        result = await engine.download_song(video_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            if status_msg:
                await status_msg.edit_text(
                    f"❌ Download failed.\n\n**Source:** YOUTUBE\n**ID:** {video_id}\n\n`{error_msg}`"
                )
            return

        data = result.get("data", {})
        title = data.get("title", "Unknown Title")
        original_filepath = data.get("filepath")

        if not original_filepath:
            if status_msg:
                await status_msg.edit_text("❌ File path not found after download.")
            return

        # ========================================================
        # FILE FINDING LOGIC
        # ========================================================
        dir_path = os.path.dirname(original_filepath)
        base_name_without_ext = os.path.splitext(original_filepath)[0]
        
        possible_file_paths = [
            original_filepath,
            f"{base_name_without_ext}.webm",
            f"{base_name_without_ext}.m4a",
            f"{base_name_without_ext}.mp3",
            f"{base_name_without_ext}.opus"
        ]
        
        actual_filepath = None
        for path in possible_file_paths:
            if os.path.exists(path):
                actual_filepath = path
                break
        
        if not actual_filepath and os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.lower().endswith(('.webm', '.m4a', '.mp3', '.opus')):
                    actual_filepath = os.path.join(dir_path, f)
                    break
                    
        if not actual_filepath:
            if status_msg:
                await status_msg.edit_text(
                    f"❌ File not found on disk.\n\nChecked extension: .webm, .m4a, .mp3, .opus\nIn folder: `{dir_path}`"
                )
            return

        # ========================================================
        # SAFE RENAME
        # ========================================================
        filename_with_ext = os.path.basename(actual_filepath)
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', filename_with_ext) 
        safe_filepath = os.path.join(dir_path, safe_filename)

        if safe_filepath != actual_filepath:
            os.rename(actual_filepath, safe_filepath)
            filepath = safe_filepath
        else:
            filepath = actual_filepath

        # ========================================================
        # UPLOAD
        # ========================================================
        if status_msg:
            await status_msg.edit_text(f"⚡ 𝘍𝘪𝘯𝘪𝘴𝘩𝘪𝘯𝘨 𝘶𝘱... `{title}`...")
        
        await client.send_audio(
            chat_id=callback.from_user.id,
            audio=filepath,
            title=title,
            performer="YouTube",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
            ])
        )

        if status_msg:
            await status_msg.delete()

        if os.path.exists(filepath):
            os.remove(filepath)

        logger.info(f"✅ SONG SENT SUCCESSFULLY: {title}")

    except Exception as e:
        logger.error(f"❌ DOWNLOAD ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await callback.answer("❌ Download failed!", show_alert=True)
        except:
            pass
        try:
            await client.send_message(
                chat_id=callback.from_user.id,
                text=f"❌ Error: `{type(e).__name__}: {e}`"
            )
        except:
            pass