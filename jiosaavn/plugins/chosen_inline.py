# jiosaavn/plugins/chosen_inline.py

import os
import re
import logging
import traceback
from pyrogram.types import ChosenInlineResult, InlineKeyboardMarkup, InlineKeyboardButton
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
from api.cache import CacheManager


logger = logging.getLogger(__name__)

print("✅ chosen_inline.py LOADED")
logger.info("✅ chosen_inline.py LOADED")

@Bot.on_chosen_inline_result()
async def chosen_inline(client: Bot, chosen: ChosenInlineResult):
    print("🔥 CHOSEN EVENT RECEIVED")
    logger.info("🔥 CHOSEN EVENT RECEIVED")
    try:
        # 🔥 YEH LOG SABSE IMPORTANT HAI
        logger.info("=" * 50)
        logger.info("🎯 CHOSEN INLINE TRIGGERED!")
        logger.info(f"✅ CHOSEN INLINE RESULT: {chosen.result_id}")
        logger.info(f"👤 USER: {chosen.from_user.id}")
        logger.info(f"📝 QUERY: {chosen.query}")
        logger.info(f"💬 CHAT ID: {chosen.chat_instance}")  # Ye group/chat ID hai
        logger.info("=" * 50)
        
        # 🔥 IMPORTANT: Sender chat ID (group ya private chat)
        # chosen.chat_instance mein group/chat ID aati hai
        chat_id = chosen.chat_instance
        
        # Agar chat_instance 0 hai toh user ki private chat hai
        if chat_id == 0:
            chat_id = chosen.from_user.id
        
        # 🔥 VIDEO ID EXTRACT
        video_id = chosen.result_id
        
        # Agar "yt_" prefix hai toh hatao
        if video_id.startswith("yt_"):
            video_id = video_id.split("_")[1]
            logger.info(f"🔑 EXTRACTED VIDEO ID: {video_id}")
        
        if not video_id:
            logger.warning("⚠️ NO VIDEO ID")
            await client.send_message(
                chat_id=chat_id,
                text="❌ Invalid Selection. Please try another song."
            )
            return

        # ========================================================
        # 🔥 SAME AS DOWNLOAD_HANDLER LOGIC
        # ========================================================
        
        # User ko batao (iss chat me bhejo)
        status_msg = await client.send_message(
            chat_id=chat_id,
            text="🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨 𝘺𝘰𝘶𝘳 𝘵𝘳𝘢𝘤𝘬..."
        )

        engine = SearchEngine()
        cache = CacheManager(client.db)
        
        # ==========================================
        # CACHE CHECK
        # ==========================================
        
        cached = await cache.get(video_id)

        if cached:
            logger.info(f"⚡ CACHE HIT: {video_id}")

            await client.send_audio(
                chat_id=chat_id,  # 🔥 Group/chat me bhejo
                audio=cached["file_id"],
                title=cached.get("title", "Unknown"),
                performer=cached.get("uploader", "YouTube"),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🎵 Search Again",
                            switch_inline_query_current_chat=""
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🤖 𝐀м𝓊ᔕ𝕀¢",
                            url="https://t.me/aartimusic_bot?start=home"
                        )
                    ]
                ])
            )

            await status_msg.delete()
            return
        
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
        # FILE FINDING LOGIC
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
        # SAFE RENAME
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
        # UPLOAD
        # ========================================================
        await status_msg.edit_text(f"⚡ 𝘍𝘪𝘯𝘪𝘴𝘩𝘪𝘯𝘨 𝘶𝘱... `{title}`...")
        
        sent = await client.send_audio(
            chat_id=chat_id,  # 🔥 Group/chat me bhejo
            audio=filepath,
            title=title,
            performer="YouTube",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")]
            ])
        )
        
        # ==========================================
        # SAVE CACHE
        # ==========================================
        
        try:
            if sent and sent.audio:
                await cache.save(
                    video_id=video_id,
                    file_id=sent.audio.file_id,
                    title=title,
                    duration=data.get("duration", 0),
                    uploader=data.get("uploader", "YouTube")
                )
                saved = await cache.save(
                    video_id=video_id,
                    file_id=sent.audio.file_id,
                    title=title,
                    duration=data.get("duration", 0),
                    uploader=data.get("uploader", "YouTube")
                )
                if saved:
                    logger.info("💾 Saved to cache")
           
        except Exception as e:
            logger.error(f"Cache save failed: {e}")
        
        await status_msg.delete()

        if os.path.exists(filepath):
            os.remove(filepath)

        logger.info(f"✅ SONG SENT SUCCESSFULLY: {title}")

    except Exception as e:
        logger.error(f"❌ CHOSEN INLINE ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await client.send_message(
                chat_id=chat_id if 'chat_id' in locals() else chosen.from_user.id,
                text=f"❌ Error: `{type(e).__name__}: {e}`"
            )
        except:
            pass