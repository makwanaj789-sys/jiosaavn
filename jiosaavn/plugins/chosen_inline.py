import os
import re
import logging
from pyrogram.types import ChosenInlineResult, InlineKeyboardMarkup, InlineKeyboardButton
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

@Bot.on_chosen_inline_result()
async def chosen_inline(client: Bot, chosen: ChosenInlineResult):
    try:
        print(f"INLINE CLICKED ID: {chosen.result_id}")

        engine = SearchEngine()
        
        # 🟢 1. Download call karo
        result = await engine.download_song(item_id=chosen.result_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await client.send_message(
                chat_id=chosen.from_user.id,
                text=f"❌ Download failed for inline selection.\n\n`{error_msg}`"
            )
            return

        data = result.get("data", {})
        title = data.get("title", "Unknown Title")
        original_filepath = data.get("filepath")

        if not original_filepath:
            await client.send_message(
                chat_id=chosen.from_user.id,
                text="❌ File path not found after download."
            )
            return

        # 🔥 2. File dhundho (Same logic as download_handler)
        dir_path = os.path.dirname(original_filepath)
        base_name = os.path.splitext(original_filepath)[0]
        possible_files = [
            original_filepath,
            f"{base_name}.webm",
            f"{base_name}.m4a",
            f"{base_name}.mp3",
            f"{base_name}.opus"
        ]
        
        actual_filepath = None
        for path in possible_files:
            if os.path.exists(path):
                actual_filepath = path
                break
        
        # Folder scan
        if not actual_filepath and os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.lower().endswith(('.webm', '.m4a', '.mp3', '.opus')):
                    actual_filepath = os.path.join(dir_path, f)
                    break

        if not actual_filepath:
            await client.send_message(
                chat_id=chosen.from_user.id,
                text=f"❌ File not found on disk in `{dir_path}`"
            )
            return

        # 🛡️ 3. Safe Rename (Fix ASCII error)
        filename = os.path.basename(actual_filepath)
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', filename)
        safe_filepath = os.path.join(dir_path, safe_filename)

        if safe_filepath != actual_filepath:
            os.rename(actual_filepath, safe_filepath)
            filepath = safe_filepath
        else:
            filepath = actual_filepath

        # 🟢 4. USER KO DIRECT DM MEIN FILE BHEJO
        await client.send_audio(
            chat_id=chosen.from_user.id,
            audio=filepath,
            title=title,
            performer="YouTube",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
            ])
        )

        # 🟢 5. Telegram ko batado ki process complete hai (Blank answer)
        # Note: Telegram allow karta hai 'chosen_inline_result' ko bina reply kare, 
        # lekin humne DM bhej diya hai toh user confuse nahi hoga.
        
        # Cleanup file
        if os.path.exists(filepath):
            os.remove(filepath)

    except Exception as e:
        logger.exception(f"Chosen Inline Error: {e}")
        try:
            await client.send_message(
                chat_id=chosen.from_user.id,
                text=f"❌ Error: `{type(e).__name__}: {e}`"
            )
        except:
            pass