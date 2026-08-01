import logging
import re  # <--- ADD THIS IMPORT
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
        filepath = data.get("filepath")

        if not filepath:
            await message.message.edit_text("❌ File path not found after download.")
            return

        # =====================================================
        # FIX: Convert the filepath to pure ASCII characters
        # =====================================================
        # This regex replaces any character that is NOT a letter, number, dot, or slash with an underscore
        safe_filepath = re.sub(r'[^a-zA-Z0-9./_\-]', '_', filepath)
        
        # If the file was moved/renamed, we must ensure the actual file on disk exists at the safe path
        import os
        if safe_filepath != filepath and os.path.exists(filepath):
            os.rename(filepath, safe_filepath)
            filepath = safe_filepath
            # Update the title to match if you want, or leave it as is
        # =====================================================

        await message.message.edit_text(f"📤 Uploading `{title}`...")
        await client.send_audio(
            chat_id=message.from_user.id,
            audio=filepath, # Now uses the safe, ASCII-only path
            title=title,
            performer="YouTube"
        )

        await message.message.delete()

    except Exception as e:
        logger.exception(f"Download callback failed: {e}")
        try:
            await message.message.edit_text(
                f"❌ An error occurred during download.\n\n`{type(e).__name__}: {e}`"
            )
        except:
            pass