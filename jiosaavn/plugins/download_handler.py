import logging
import re
import os
from pyrogram.types import Message, CallbackQuery
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

@Bot.on_callback_query(filters=None)
async def download_callback(client: Bot, message: CallbackQuery):
    try:
        await message.answer()
        data = message.data

        if not data.startswith("youtube#"): return

        video_id = data.split("#")[1]
        if not video_id:
            await message.message.edit_text("❌ Invalid video ID.")
            return

        engine = SearchEngine()
        await message.message.edit_text("⏳ Downloading audio from YouTube... Please wait.")

        result = await engine.download_song(video_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await message.message.edit_text(
                f"❌ Download failed.\n\n**Source:** YOUTUBE\n**ID:** {video_id}\n\n`{error_msg}`"
            )
            return

        data = result.get("data", {})
        title = data.get("title", "Unknown Title")
        original_filepath = data.get("filepath")

        if not original_filepath:
            await message.message.edit_text("❌ File path not found after download.")
            return

        # ========================================================
        # 🔥 ULTIMATE FIX: Actual downloaded file ko dhundho
        # ========================================================
        
        # 1. Folder ka path alag karo
        dir_path = os.path.dirname(original_filepath)
        
        # 2. Filename ka base (bina extension ke) nikaalo
        base_name_without_ext = os.path.splitext(original_filepath)[0]
        
        # 3. Dono check karo -> Pehle exact path, phir .webm, phir .m4a, phir .mp3
        possible_file_paths = [
            original_filepath, # Jo engine ne diya
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
        
        # Agar folder mein kuch nahi mila, toh folder ka scan karo
        if not actual_filepath and os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.lower().endswith(('.webm', '.m4a', '.mp3', '.opus')):
                    actual_filepath = os.path.join(dir_path, f)
                    break
                    
        # Agar kuch bhi nahi mila toh error do
        if not actual_filepath:
            await message.message.edit_text(
                f"❌ File not found on disk.\n\n"
                f"Checked extension: .webm, .m4a, .mp3, .opus\n"
                f"In folder: `{dir_path}`"
            )
            return

        # ========================================================
        # 🛡️ SAFE RENAME: Special characters hatao (ASCII error fix)
        # ========================================================
        filename_with_ext = os.path.basename(actual_filepath)
        # Replace spaces, brackets, hash, pipe, etc. with underscore '_'
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', filename_with_ext) 
        safe_filepath = os.path.join(dir_path, safe_filename)

        # Agar naam alag hai toh rename karo
        if safe_filepath != actual_filepath:
            os.rename(actual_filepath, safe_filepath)
            filepath = safe_filepath
        else:
            filepath = actual_filepath
        # ========================================================

        await message.message.edit_text(f"📤 Uploading `{title}`...")
        
        # Ab file upload karo
        await client.send_audio(
            chat_id=message.from_user.id,
            audio=filepath, 
            title=title,
            performer="YouTube"
        )

        await message.message.delete()

        # File cleanup (Optional: Upload ke baad file delete kar do)
        if os.path.exists(filepath):
            os.remove(filepath)

    except Exception as e:
        logger.exception(f"Download callback failed: {e}")
        try:
            await message.message.edit_text(
                f"❌ An error occurred during download.\n\n`{type(e).__name__}: {e}`"
            )
        except:
            pass