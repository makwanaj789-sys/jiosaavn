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
        
        # 🔥 Agar ID hi nahi hai toh wapas bhejo
        if not chosen.result_id:
            logger.warning("⚠️ NO RESULT ID")
            await client.send_message(
                chat_id=chosen.from_user.id,
                text="❌ Invalid Selection. Please try another song."
            )
            return

        # User ko batao ke download start ho gaya
        status_msg = await client.send_message(
            chat_id=chosen.from_user.id,
            text=f"⏳ Downloading your song... Please wait."
        )

        engine = SearchEngine()
        
        # 1. Download call karo
        logger.info(f"📥 DOWNLOADING: {chosen.result_id}")
        result = await engine.download_song(item_id=chosen.result_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"❌ DOWNLOAD FAILED: {error_msg}")
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
        # 🔥 FILE KO DHUNDHO
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
        
        # Agar folder mein kuch nahi mila, toh folder ka scan karo
        if not actual_filepath and os.path.exists(dir_path):
            logger.info(f"🔍 SCANNING FOLDER: {dir_path}")
            for f in os.listdir(dir_path):
                if f.lower().endswith(('.webm', '.m4a', '.mp3', '.opus')):
                    actual_filepath = os.path.join(dir_path, f)
                    logger.info(f"✅ FILE FOUND IN FOLDER: {f}")
                    break
                    
        # Agar kuch bhi nahi mila toh error do
        if not actual_filepath:
            logger.error(f"❌ FILE NOT FOUND IN: {dir_path}")
            await status_msg.edit_text(
                text=f"❌ File not found on disk.\nIn folder: `{dir_path}`"
            )
            return

        # ========================================================
        # 🛡️ SAFE RENAME: Special characters hatao
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

        # 2. USER KO DIRECT DM MEIN FILE BHEJO
        logger.info(f"📤 UPLOADING: {title}")
        await status_msg.edit_text(
            text=f"📤 Uploading `{title}`..."
        )
        
        await client.send_audio(
            chat_id=chosen.from_user.id,
            audio=filepath,
            title=title,
            performer="YouTube",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
            ])
        )

        # Status message delete karo
        await status_msg.delete()

        # Cleanup file
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"🧹 FILE DELETED: {filepath}")

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