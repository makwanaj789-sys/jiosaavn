import html
import logging
import traceback
import asyncio

from api.search_engine import SearchEngine
from jiosaavn.bot import Bot

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

# Post Creator state check
from jiosaavn.plugins.admin import is_post_creator_active

logger = logging.getLogger(__name__)

def safe_text(value, default="Unknown"):
    if value is None: return default
    try: return html.unescape(str(value))
    except: return default

def safe_dict(value):
    return value if isinstance(value, dict) else {}

def safe_list(value):
    return value if isinstance(value, list) else []

private_search_filter = (filters.text & filters.incoming & filters.private & ~filters.regex(r"^https?://") & ~filters.via_bot & ~filters.command(["start", "settings", "help", "about", "admin", "cancel"]))
group_search_filter = (filters.command("am") & filters.incoming)

@Bot.on_callback_query(filters.regex(r"^search#"))
@Bot.on_message(private_search_filter | group_search_filter)
async def search(client: Bot, message: Message | CallbackQuery):
    send_msg = None
    try:
        if isinstance(message, Message):
            if message.from_user and is_post_creator_active(message.from_user.id): return
            send_msg = await message.reply("__**Processing... ⏳**__", quote=True)
            raw_text = (message.text or "").strip()
            if message.chat.type == ChatType.PRIVATE:
                query = raw_text
            else:
                parts = raw_text.split(maxsplit=1)
                if len(parts) < 2:
                    return await send_msg.edit("❌ Please enter a song name.\n\n**Example:**\n`/am Alan Walker Spectre`")
                query = parts[1].strip()
                if not query:
                    return await send_msg.edit("❌ Please enter a song name.\n\n**Example:**\n`/am Alan Walker Spectre`")
            try:
                user_data = await client.db.get_user(message.from_user.id)
            except:
                logger.exception("Failed to get user settings")
                user_data = {}
            if not isinstance(user_data, dict): user_data = {}
            search_type = user_data.get("type") or "all"
            page_no = 1
        else:
            await message.answer()
            send_msg = message.message
            callback_data = message.data or ""
            data = callback_data.split("#")
            search_type = data[1] if len(data) > 1 and data[1] else "all"
            page_no = 1
            if len(data) >= 3:
                try: page_no = int(data[2])
                except: page_no = 1
            reply_message = message.message.reply_to_message
            if reply_message and reply_message.text:
                query = (reply_message.text or "").strip()
                if query.lower().startswith("/am"):
                    parts = query.split(maxsplit=1)
                    if len(parts) >= 2: query = parts[1].strip()
                    else: query = ""
            else:
                return await send_msg.edit("❌ Could not find the original search query.")
        if not query: return await send_msg.edit("❌ Please enter a song name.")
        if isinstance(message, Message):
            try:
                user_id = message.from_user.id if message.from_user else 0
                chat_id = message.chat.id
                if user_id:
                    await client.db.get_user(user_id)
                    await client.db.add_search(user_id=user_id, chat_id=chat_id)
                if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    await client.db.add_group(chat_id)
            except: logger.exception("Failed to save search analytics")

        engine = None
        response = None
        
                try:
            engine = SearchEngine()
            logger.info(f"Searching YouTube for: {query}")
            response = await engine.search(query=query, source="youtube", search_type=search_type, page_no=page_no)
            
            has_results = False
            if response:
                # 🌟 FIX START: Handle List (YouTube) and Dict (JioSaavn)
                if search_type in ("all", "topquery"):
                    # Agar all/topquery hai toh songs key check karo
                    if isinstance(response, dict):
                        songs_data = safe_list(response.get("songs", {}).get("data", []))
                        if songs_data: has_results = True
                else:
                    # specific search (songs, albums...)
                    if isinstance(response, list):
                        # YouTube nayi search list return karta hai
                        if response:
                            has_results = True
                    elif isinstance(response, dict):
                        # JioSaavn dict return karta hai
                        results_data = safe_list(response.get("results", []))
                        if results_data:
                            has_results = True
                        else:
                            for key in response:
                                if key not in ["total", "position"]:
                                    data = safe_list(response.get(key, {}).get("data", []) if isinstance(response, dict) else [])
                                    if data:
                                        has_results = True
                                        break
                # 🌟 FIX END

            # Agar YouTube mein results nahi mile toh JioSaavn pe jao
            if not has_results:
                logger.info(f"No YouTube results for '{query}'. Falling back to JioSaavn.")
                response = await engine.search(query=query, source="jiosaavn", search_type=search_type, page_no=page_no)
                
        except Exception as e:
            logger.exception(f"YouTube search failed: {e}")
            try:
                logger.info(f"Falling back to JioSaavn for '{query}'")
                engine = SearchEngine()
                response = await engine.search(query=query, source="jiosaavn", search_type=search_type, page_no=page_no)
            except Exception as fallback_error:
                logger.exception(f"JioSaavn fallback also failed: {fallback_error}")
                return await send_msg.edit(f"❌ Search failed on both YouTube and JioSaavn.\n\n`{type(fallback_error).__name__}: {fallback_error}`")