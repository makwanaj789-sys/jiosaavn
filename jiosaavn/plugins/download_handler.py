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

        # =========================================================
        # 🛠️ FIX: Check for .mp3, .m4a, OR .webm extensions
        # =========================================================
        dir_path = os.path.dirname(original_filepath)
        base_name_without_ext = os.path.splitext(original_filepath)[0] # .NA ya bad extension hata diya
        
        # Check karo ki actual file kis extension mein exist karti hai
        possible_extensions = ['.mp3', '.m4a', '.webm']
        actual_filepath = None
        
        for ext in possible_extensions:
            test_path = f"{base_name_without_ext}{ext}"
            if os.path.exists(test_path):
                actual_filepath = test_path
                break
        
        # Agar koi bhi extension match nahi kiya
        if actual_filepath is None:
            await message.message.edit_text("❌ File not found on disk (checked .mp3, .m4a, and .webm).")
            return

        # Ab file path ko SAFE (ASCII) banayenge taaki upload ho sake
        filename_with_ext = os.path.basename(actual_filepath)
        # File name se saare special characters hatao (space, [ ], #, etc. sabko '_' se replace karo)
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', filename_with_ext) 
        safe_filepath = os.path.join(dir_path, safe_filename)

        # Agar safe filename original se alag hai, toh file ko rename karo
        if safe_filepath != actual_filepath:
            os.rename(actual_filepath, safe_filepath)
            filepath = safe_filepath
        else:
            filepath = actual_filepath
        # =========================================================

        await message.message.edit_text(f"📤 Uploading `{title}`...")
        
        # Safe filepath send karo
        await client.send_audio(
            chat_id=message.from_user.id,
            audio=filepath, 
            title=title,
            performer="YouTube"
        )

        await message.message.delete()

        # Optional: File cleanup (hatao agar jagah bachani hai)
        # if os.path.exists(filepath):
        #     os.remove(filepath)

    except Exception as e:
        logger.exception(f"Download callback failed: {e}")
        try:
            await message.message.edit_text(
                f"❌ An error occurred during download.\n\n`{type(e).__name__}: {e}`"
            )
        except:
            pass