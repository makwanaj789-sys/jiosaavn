# jiosaavn/plugins/download_callback.py

import os
import re
import logging
import traceback
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
from api.cache import CacheManager


logger = logging.getLogger(__name__)

@Bot.on_callback_query()
async def download_callback(client: Bot, callback: CallbackQuery):
    """
    Handle download callbacks from inline results
    """
    try:
        data = callback.data
        
        if not data.startswith("download_"):
            return
        
        video_id = data.replace("download_", "")
        chat_id = callback.message.chat.id
        user_id = callback.from_user.id
        
        # 🔥 USER KO BATAO
        await callback.answer("⏳ Downloading your song... Please wait!")
        
        status_msg = await callback.message.edit_text(
            f"🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨 𝘺𝘰𝘶𝘳 𝘵𝘳𝘢𝘤𝘬...\n\n"
            f"⏳ This may take a few seconds...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ Processing...", callback_data="none")]
            ])
        )
        
        engine = SearchEngine()
        cache = CacheManager(client.db)
        
        # ==========================================
        # DOWNLOAD SONG
        # ==========================================
        result = await engine.download_song(video_id)
        
        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await status_msg.edit_text(
                f"❌ Download failed.\n\n**Error:** {error_msg}"
            )
            return
        
        data = result.get("data", {})
        title = data.get("title", "Unknown Title")
        original_filepath = data.get("filepath")
        
        if not original_filepath:
            await status_msg.edit_text("❌ File path not found after download.")
            return
        
        # ==========================================
        # FIND FILE
        # ==========================================
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
            await status_msg.edit_text(
                f"❌ File not found on disk.\n\n"
                f"In folder: `{dir_path}`"
            )
            return
        
        # ==========================================
        # SAFE RENAME
        # ==========================================
        filename_with_ext = os.path.basename(actual_filepath)
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', filename_with_ext) 
        safe_filepath = os.path.join(dir_path, safe_filename)
        
        if safe_filepath != actual_filepath:
            os.rename(actual_filepath, safe_filepath)
            filepath = safe_filepath
        else:
            filepath = actual_filepath
        
        # ==========================================
        # UPLOAD TO CHAT (GROUP/PRIVATE)
        # ==========================================
        await status_msg.edit_text(
            f"⚡ 𝘜𝘱𝘭𝘰𝘢𝘥𝘪𝘯𝘨... `{title}`...\n\n"
            f"📤 Sending to chat..."
        )
        
        sent = await client.send_audio(
            chat_id=chat_id,  # USI CHAT MEIN BHEJO
            audio=filepath,
            title=title,
            performer=data.get("uploader", "YouTube"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
            ])
        )
        
        # ==========================================
        # SAVE TO CACHE
        # ==========================================
        try:
            if sent and sent.audio:
                await cache.save(
                    video_id=video_id,
                    file_id=sent.audio.file_id,
                    title=title,
                    duration=data.get("duration", 0),
                    uploader=data.get("uploader", "YouTube")
                )
                logger.info(f"💾 CACHE SAVED: {title}")
        except Exception as e:
            logger.error(f"Cache save failed: {e}")
        
        # ==========================================
        # CLEANUP
        # ==========================================
        await status_msg.delete()
        
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"🗑️ DELETED: {filepath}")
        
        logger.info(f"✅ SONG SENT: {title}")
        
    except Exception as e:
        logger.error(f"❌ DOWNLOAD CALLBACK ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await callback.message.edit_text(
                f"❌ Error: `{type(e).__name__}: {e}`"
            )
        except:
            pass