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
        
        # 🔥 VIDEO ID EXTRACT
        video_id = chosen.result_id
        
        # Agar "yt_" prefix hai toh hatao
        if video_id.startswith("yt_"):
            video_id = video_id.split("_")[1]
            logger.info(f"🔑 EXTRACTED VIDEO ID: {video_id}")
        
        if not video_id:
            logger.warning("⚠️ NO VIDEO ID")
            await client.send_message(
                chat_id=chosen.from_user.id,
                text="❌ Invalid Selection. Please try another song."
            )
            return

        # ========================================================
        # 🔥 SAME AS DOWNLOAD_HANDLER LOGIC
        # ========================================================
        
        # User ko batao
        status_msg = await client.send_message(
            chat_id=chosen.from_user.id,
            text="⏳ Downloading audio from YouTube... Please wait."
        )

        engine = SearchEngine()
        result = await engine.download_song(video_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await status_msg.edit_text(
                f"❌ Download failed.\n\n**Source:** YOUTUBE\n**ID:** {video_id}\n\n`{error_msg}`"
            )
            return

        data = result.get("data", {})
        title = data.get("title", "Unknown Title")
        original_filepath = data.get("filepath")

        if not original_filepath:
            await status_msg.edit_text("❌ File path not found after download.")
            return

        # ========================================================
        # FILE FINDING LOGIC (Same as download_handler)
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
            await status_msg.edit_text(
                f"❌ File not found on disk.\n\n"
                f"Checked extension: .webm, .m4a, .mp3, .opus\n"
                f"In folder: `{dir_path}`"
            )
            return

        # ========================================================
        # SAFE RENAME (Same as download_handler)
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
        # UPLOAD (Same as download_handler)
        # ========================================================
        await status_msg.edit_text(f"📤 Uploading `{title}`...")
        
        await client.send_audio(
            chat_id=chosen.from_user.id,
            audio=filepath,
            title=title,
            performer="YouTube",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
            ])
        )

        await status_msg.delete()

        if os.path.exists(filepath):
            os.remove(filepath)

        logger.info(f"✅ SONG SENT SUCCESSFULLY: {title}")

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