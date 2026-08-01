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

        # 🔥 Agar ID hi nahi hai toh wapas bhejo (Playlist case handle)
        if not chosen.result_id:
            await client.send_message(
                chat_id=chosen.from_user.id,
                text="❌ Invalid Selection. Please try another song."
            )
            return

        engine = SearchEngine()
        
        # 1. Download call karo
        result = await engine.download_song(item_id=chosen.result_id)

        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            await client.send_message(
                chat_id=chosen.from_user.id,
                text=f"❌ Download failed.\n\n`{error_msg}`"
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

        # ========================================================
        # 🔥 COPY OF DOWNLOAD_HANDLER LOGIC: File ko dhundho
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
        
        # Agar folder mein kuch nahi mila, toh folder ka scan karo
        if not actual_filepath and os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.lower().endswith(('.webm', '.m4a', '.mp3', '.opus')):
                    actual_filepath = os.path.join(dir_path, f)
                    break
                    
        # Agar kuch bhi nahi mila toh error do
        if not actual_filepath:
            await client.send_message(
                chat_id=chosen.from_user.id,
                text=f"❌ File not found on disk.\nIn folder: `{dir_path}`"
            )
            return

        # ========================================================
        # 🛡️ SAFE RENAME: Special characters hatao (ASCII error fix)
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

        # 2. USER KO DIRECT DM MEIN FILE BHEJO
        await client.send_audio(
            chat_id=chosen.from_user.id,
            audio=filepath,
            title=title,
            performer="YouTube",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
            ])
        )

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