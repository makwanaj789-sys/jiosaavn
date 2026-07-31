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
            
            # 🔥 AB SIRF YOUTUBE HAI, ISLIYE SEARCH_TYPE ALL HI RAKHENGE
            search_type = "all" 
            page_no = 1
        else:
            await message.answer()
            send_msg = message.message
            callback_data = message.data or ""
            data = callback_data.split("#")
            
            # 🔥 AB SIRF YOUTUBE HAI, ISLIYE CALLBACK MEIN SONG TYPE NAHI DEKHENGE
            search_type = "all" 
            page_no = 1
            if len(data) >= 2:
                try: page_no = int(data[1])
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
            
            # 🔥 AB SIRF YOUTUBE SEARCH HOGA
            response = await engine.search(
                query=query, 
                page_no=page_no
            )
            
        except Exception as e:
            logger.exception(f"YouTube search failed: {e}")
            return await send_msg.edit(f"❌ YouTube search failed.\n\n`{type(e).__name__}: {e}`")

        if not response:
            return await send_msg.edit(f"🔎 No search result found for your query `{query}`")
        
        # 🔥 RESPONSE VALIDATION (SIRF YOUTUBE LIST)
        results = safe_list(response.get("results", []))
        total_results = response.get("total", 0)

        buttons = []

        for result in results:
            if not isinstance(result, dict): continue

            title = safe_text(result.get("title"))
            item_id = safe_text(result.get("id"))
            artist = safe_text(result.get("artist"), "Unknown Artist")
            duration = safe_text(result.get("duration_str"), "N/A")

            if not item_id: continue

            # 🔥 BUTTON TEXT (Song name from Artist)
            button_text = f"🎙 {title} by {artist} ({duration})"
            
            # 🔥 SIDHA YOUTUBE ID SE CALLBACK
            callback_data = f"youtube#{item_id}"
            
            buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

        if not buttons:
            return await send_msg.edit(f"🔎 No search result found for your query `{query}`")

        text = (
            f"**📈 Total Results:** {total_results}\n\n"
            f"**🔍 Search Query:** {query}\n\n"
            f"**📜 Page No:** {page_no}\n\n"
            f"__Select a song to play or download 👇__"
        )

        # 🔥 PAGINATION (Next / Previous buttons)
        navigation_buttons = []
        if page_no > 1:
            navigation_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"search#{page_no - 1}"))
        if total_results > (10 * page_no):
            navigation_buttons.append(InlineKeyboardButton("➡️", callback_data=f"search#{page_no + 1}"))
        if navigation_buttons: buttons.append(navigation_buttons)

        # 🔥 CLOSE BUTTON
        buttons.append([InlineKeyboardButton("Close ❌", callback_data="close")])
        
        await send_msg.edit(text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.exception("Error inside search handler")
        traceback.print_exc()
        try:
            if send_msg: await send_msg.edit(f"❌ Something went wrong.\n\n`{type(e).__name__}: {e}`")
        except: logger.exception("Failed to display search error")