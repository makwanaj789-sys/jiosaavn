# jiosaavn/plugins/download_callback.py

import os
import re
import logging
import traceback
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from jiosaavn.bot import Bot
from api.search_engine import SearchEngine
from api.cache import CacheManager


logger = logging.getLogger(__name__)

# 🔥 DEBUG: Check if file is loading
print("=" * 50)
print("📦 DOWNLOAD_CALLBACK.PY LOADED ✅")
print("=" * 50)
logger.info("📦 DOWNLOAD_CALLBACK.PY LOADED")

@Bot.on_callback_query()
async def download_callback(client: Bot, callback: CallbackQuery):
    """
    Handle download callbacks from inline results
    """
    # 🔥 DEBUG: Check if callback is triggered
    print(f"🔥 CALLBACK TRIGGERED: {callback.data}")
    logger.info(f"🔥 CALLBACK TRIGGERED: {callback.data}")
    
    try:
        data = callback.data
        
        if not data.startswith("download_"):
            print(f"⏭️ SKIPPING: Not a download callback ({data})")
            return
        
        video_id = data.replace("download_", "")
        chat_id = callback.message.chat.id
        user_id = callback.from_user.id
        
        print(f"📥 DOWNLOAD REQUEST: video_id={video_id}, chat_id={chat_id}, user={user_id}")
        
        # 🔥 USER KO BATAO
        await callback.answer("⏳ Downloading your song... Please wait!")
        
        status_msg = await callback.message.edit_text(
            f"🎵 𝘍𝘦𝘵𝘤𝘩𝘪𝘯𝘨 𝘺𝘰𝘶𝘳 𝘵𝘳𝘢𝘤𝘬...\n\n"
            f"⏳ This may take a few seconds...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏳ Processing...", callback_data="none")]
            ])
        )
        
        engine = SearchEngine()
        cache = CacheManager(client.db)
        
        # ==========================================
        # DOWNLOAD SONG
        # ==========================================
        print(f"⬇️ DOWNLOADING: {video_id}")
        result = await engine.download_song(video_id)
        
        if not result or not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            print(f"❌ DOWNLOAD FAILED: {error_msg}")
            await status_msg.edit_text(
                f"❌ Download failed.\n\n**Error:** {error_msg}"
            )
            return
        
        data = result.get("data", {})
        title = data.get("title", "Unknown Title")
        original_filepath = data.get("filepath")
        
        print(f"✅ DOWNLOAD COMPLETE: {title} - {original_filepath}")
        
        if not original_filepath:
            await status_msg.edit_text("❌ File path not found after download.")
            return
        
        # ... rest of the code remains same ...
        
    except Exception as e:
        print(f"❌ DOWNLOAD CALLBACK ERROR: {e}")
        print(traceback.format_exc())
        logger.error(f"❌ DOWNLOAD CALLBACK ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await callback.message.edit_text(
                f"❌ Error: `{type(e).__name__}: {e}`"
            )
        except:
            pass