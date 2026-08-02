import os
import re
import logging
import traceback
from pyrogram.types import ChosenInlineResult, InlineKeyboardMarkup, InlineKeyboardButton
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

@Bot.on_chosen_inline_result()
async def chosen_inline(client: Bot, chosen: ChosenInlineResult):
    try:
        logger.info(f"✅ CHOSEN INLINE RESULT: {chosen.result_id}")
        logger.info(f"👤 USER: {chosen.from_user.id}")
        logger.info(f"📝 QUERY: {chosen.query}")
        
        # 🔥 FIX: Result ID se video ID extract karo
        result_id = chosen.result_id
        
        # Agar result_id "yt_" se start ho toh video ID extract karo
        if result_id.startswith("yt_"):
            video_id = result_id.split("_")[1]
            logger.info(f"🔑 EXTRACTED VIDEO ID: {video_id}")
        else:
            video_id = result_id
            logger.info(f"🔑 USING RAW ID: {video_id}")
        
        if not video_id:
            logger.warning("⚠️ NO VIDEO ID")
            await client.send_message(
                chat_id=chosen.from_user.id,
                text="❌ Invalid Selection. Please try another song."
            )
            return

        # User ko batao
        status_msg = await client.send_message(
            chat_id=chosen.from_user.id,
            text=f"⏳ Downloading your song... Please wait."
        )

        engine = SearchEngine()
        
        # 🔥 FIX: Video ID se download karo
        logger.info(f"📥 DOWNLOADING: {video_id}")
        result = await engine.download_song(item_id=video_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"❌ DOWNLOAD FAILED: {error_msg}")
            
            # 🔥 FIX: Better error message
            if "ffmpeg" in error_msg.lower():
                error_msg = "FFmpeg not installed. Please install FFmpeg."
            elif "cookies" in error_msg.lower():
                error_msg = "YouTube cookies required. Please set YOUTUBE_COOKIES."
            
            await status_msg.edit_text(
                text=f"❌ Download failed.\n\n`{error_msg}`"
            )
            return

        data = result.get("data", {})
        title = data.get("title", "Unknown Title")
        original_filepath = data.get("filepath")

        if not original_filepath:
            logger.error("❌ NO FILEPATH")
            await status_msg.edit_text(
                text="❌ File path not found after download."
            )
            return

        # ========================================================
        # FILE KO DHUNDHO
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
                logger.info(f"✅ FILE FOUND: {path}")
                break
        
        if not actual_filepath and os.path.exists(dir_path):
            logger.info(f"🔍 SCANNING FOLDER: {dir_path}")
            for f in os.listdir(dir_path):
                if f.lower().endswith(('.webm', '.m4a', '.mp3', '.opus')):
                    actual_filepath = os.path.join(dir_path, f)
                    logger.info(f"✅ FILE FOUND IN FOLDER: {f}")
                    break
                    
        if not actual_filepath:
            logger.error(f"❌ FILE NOT FOUND")
            await status_msg.edit_text(
                text=f"❌ File not found on disk.\nFolder: `{dir_path}`"
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
            logger.info(f"✅ RENAMED TO: {safe_filename}")
        else:
            filepath = actual_filepath

        # ========================================================
        # FILE UPLOAD
        # ========================================================
        logger.info(f"📤 UPLOADING: {title}")
        await status_msg.edit_text(
            text=f"📤 Uploading `{title}`..."
        )
        
        # 🔥 FIX: Try send_audio with different parameters
        try:
            await client.send_audio(
                chat_id=chosen.from_user.id,
                audio=filepath,
                title=title,
                performer="YouTube",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
                ])
            )
        except Exception as upload_error:
            logger.error(f"❌ UPLOAD ERROR: {upload_error}")
            # Try with different method
            await client.send_document(
                chat_id=chosen.from_user.id,
                document=filepath,
                caption=f"🎵 {title}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
                ])
            )

        await status_msg.delete()

        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"🧹 FILE DELETED")

        logger.info(f"✅ SONG SENT SUCCESSFULLY")

    except Exception as e:
        logger.error(f"❌ CHOSEN INLINE ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await client.send_message(
                chat_id=chosen.from_user.id,
                text=f"❌ Error: `{type(e).__name__}: {e}`"
            )
        except:
            pass