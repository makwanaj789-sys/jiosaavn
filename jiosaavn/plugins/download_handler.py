import logging
from pyrogram.types import Message, CallbackQuery
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

@Bot.on_callback_query(filters=None)  # Filter will be added dynamically or via regex
async def download_callback(client: Bot, message: CallbackQuery):
    try:
        await message.answer()
        data = message.data

        if not data.startswith("youtube#"):
            return

        # Video ID nikaalo
        video_id = data.split("#")[1]
        if not video_id:
            await message.message.edit_text("❌ Invalid video ID.")
            return

        # Download Engine ko call karo
        engine = SearchEngine()

        # Message show karo
        await message.message.edit_text("⏳ Downloading audio from YouTube... Please wait.")

        # Download karo
        result = await engine.download_song(video_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await message.edit(
                f"❌ Download failed.\n\n**Source:** YOUTUBE\n**ID:** {video_id}\n\n`{error_msg}`"
            )
            return

        data = result.get("data", {})

        title = data.get("title", "Unknown Title")
        filepath = data.get("filepath")

        if not filepath:
            await message.message.edit_text("❌ File path not found after download.")
            return

        # ⭐ User ko file bhej do
        await message.message.edit_text(f"📤 Uploading `{title}`...")
        await client.send_audio(
            chat_id=message.from_user.id,
            audio=filepath,
            title=title,
            performer="YouTube"
        )

        await message.delete()

        # File cleanup (optional - agar aap chahe toh)
        # import os
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