import logging
import re
import os
import aiofiles  # Agar pehle se installed hai toh use karein, warna standard 'os' use karein
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
        # 🛠️ FIX: Safe filename create karna (Extension zaroori hai)
        # ========================================================
        # File path mein extension dhundho (.mp3, .m4a, etc.)
        dir_path = os.path.dirname(original_filepath)
        filename_with_ext = os.path.basename(original_filepath)
        
        # Agar extension 'NA' hai toh .mp3 assume karo (kyunki aap audio download kar rahe ho)
        if not os.path.exists(original_filepath):
            if original_filepath.endswith('.NA'):
                original_filepath = original_filepath.replace('.NA', '.mp3')
                filename_with_ext = filename_with_ext.replace('.NA', '.mp3')
                
                # Check karo ki .mp3 version exists karta hai ya nahi
                if not os.path.exists(original_filepath):
                    await message.message.edit_text("❌ File not found on disk (neither .NA nor .mp3).")
                    return

        # Ab filename ko clean karo (Sirf safe characters allow karo)
        # [ ] ( ) # | , & space sabko underscore (_) se replace kar do
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', filename_with_ext) 
        
        # Naya safe path banao
        safe_filepath = os.path.join(dir_path, safe_filename)

        # Agar filename change hui hai toh file ko rename karo
        if safe_filepath != original_filepath:
            if os.path.exists(original_filepath):
                os.rename(original_filepath, safe_filepath)
                filepath = safe_filepath
            else:
                # Agar original nahi mila par safe path pehle se hai toh wahi use karo
                if os.path.exists(safe_filepath):
                    filepath = safe_filepath
                else:
                    await message.message.edit_text("❌ File missing before upload.")
                    return
        else:
            filepath = original_filepath
        # ========================================================

        await message.message.edit_text(f"📤 Uploading `{title}`...")
        
        # Safe filepath send karo
        await client.send_audio(
            chat_id=message.from_user.id,
            audio=filepath, 
            title=title,
            performer="YouTube"
        )

        await message.message.delete()

        # Cleanup optional
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