import logging
import aiohttp

from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from jiosaavn.bot import Bot
from jiosaavn.config.settings import OWNER_ID, BOT_TOKEN


logger = logging.getLogger(__name__)


# =========================================================
# POST CREATOR SESSIONS
# =========================================================

POST_SESSIONS = {}


def is_owner(user_id: int) -> bool:
    return bool(
        user_id
        and OWNER_ID
        and user_id == OWNER_ID
    )


def is_post_creator_active(user_id: int) -> bool:
    return user_id in POST_SESSIONS


# =========================================================
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 Refresh Stats",
                    callback_data="admin_refresh"
                )
            ],
            [
                InlineKeyboardButton(
                    "📝 Create Post",
                    callback_data="admin_create_post"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Close",
                    callback_data="admin_close"
                )
            ]
        ]
    )


# =========================================================
# POST MENU
# =========================================================

def post_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Add Button",
                    callback_data="post_add_button"
                )
            ],
            [
                InlineKeyboardButton(
                    "👀 Preview",
                    callback_data="post_preview"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="post_cancel"
                )
            ]
        ]
    )


# =========================================================
# ADMIN PANEL TEXT
# =========================================================

async def get_admin_panel_text(client: Bot):

    stats = await client.db.get_admin_stats()

    return (
        "👑 **AARTI MUSIC • ADMIN PANEL**\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "👥 **USERS & GROUPS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 **Total Users:** "
        f"`{stats.get('total_users', 0):,}`\n"

        f"👥 **Total Groups:** "
        f"`{stats.get('total_groups', 0):,}`\n"

        f"🟢 **Active Today:** "
        f"`{stats.get('active_today', 0):,}`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🎵 **MUSIC ANALYTICS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🔎 **Total Searches:** "
        f"`{stats.get('total_searches', 0):,}`\n"

        f"📅 **Today's Searches:** "
        f"`{stats.get('searches_today', 0):,}`"
    )


# =========================================================
# /ADMIN
# =========================================================

@Bot.on_message(
    filters.command("admin")
    & filters.private
)
async def admin_panel(client: Bot, message: Message):

    if not message.from_user:
        return

    if not is_owner(message.from_user.id):
        return

    try:

        text = await get_admin_panel_text(client)

        await message.reply(
            text,
            reply_markup=admin_keyboard()
        )

    except Exception as e:

        logger.exception("Admin panel error")

        await message.reply(
            "❌ Admin panel error:\n"
            f"`{type(e).__name__}: {e}`"
        )


# =========================================================
# REFRESH
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^admin_refresh$")
)
async def admin_refresh(client: Bot, callback: CallbackQuery):

    if not is_owner(callback.from_user.id):
        return await callback.answer(
            "Not allowed.",
            show_alert=True
        )

    try:

        text = await get_admin_panel_text(client)

        await callback.message.edit_text(
            text,
            reply_markup=admin_keyboard()
        )

        await callback.answer("Updated ✅")

    except Exception:

        logger.exception("Stats refresh error")

        await callback.answer(
            "Refresh failed.",
            show_alert=True
        )


# =========================================================
# CREATE POST
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^admin_create_post$")
)
async def create_post(client: Bot, callback: CallbackQuery):

    if not is_owner(callback.from_user.id):
        return await callback.answer(
            "Not allowed.",
            show_alert=True
        )

    user_id = callback.from_user.id

    POST_SESSIONS[user_id] = {
        "step": "message",

        # post
        "type": None,
        "text": None,
        "file_id": None,

        # keyboard
        # Example:
        # [
        #   [button1],
        #   [button2, button3]
        # ]
        "button_rows": [],

        "current_button": None
    }

    await callback.answer()

    await callback.message.edit_text(
        "📝 **AARTI POST CREATOR**\n\n"

        "Ab post bhejo.\n\n"

        "Supported:\n"
        "📝 Text Message\n"
        "🖼 Photo\n"
        "🎬 Video\n\n"

        "Media ke saath caption optional hai.\n\n"

        "❌ Cancel karne ke liye /cancel"
    )


# =========================================================
# CANCEL
# =========================================================

@Bot.on_message(
    filters.command("cancel")
    & filters.private
)
async def cancel_creator(client: Bot, message: Message):

    if not message.from_user:
        return

    if not is_owner(message.from_user.id):
        return

    POST_SESSIONS.pop(
        message.from_user.id,
        None
    )

    await message.reply(
        "❌ Post Creator cancelled."
    )


# =========================================================
# GET CUSTOM EMOJI FROM BUTTON NAME
# =========================================================

def get_custom_emoji_id(message: Message):

    try:

        entities = message.entities or []

        for entity in entities:

            if str(entity.type).lower().endswith(
                "custom_emoji"
            ):

                emoji_id = getattr(
                    entity,
                    "custom_emoji_id",
                    None
                )

                if emoji_id:
                    return str(emoji_id)

    except Exception:
        logger.exception(
            "Custom emoji detection failed"
        )

    return None


# =========================================================
# SAVE MEDIA/TEXT POST
# =========================================================

@Bot.on_message(
    filters.private
    & (
        filters.text
        | filters.photo
        | filters.video
    )
    & ~filters.command([
        "admin",
        "cancel",
        "start",
        "settings",
        "help",
        "about"
    ]),
    group=-5
)
async def post_creator_input(
    client: Bot,
    message: Message
):

    if not message.from_user:
        return

    user_id = message.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    step = session.get("step")


    # =====================================================
    # RECEIVE POST
    # =====================================================

    if step == "message":

        # TEXT
        if message.text:

            session["type"] = "text"
            session["text"] = message.text
            session["file_id"] = None

        # PHOTO
        elif message.photo:

            session["type"] = "photo"
            session["text"] = message.caption or ""
            session["file_id"] = message.photo.file_id

        # VIDEO
        elif message.video:

            session["type"] = "video"
            session["text"] = message.caption or ""
            session["file_id"] = message.video.file_id

        else:

            return await message.reply(
                "❌ Unsupported media."
            )

        session["step"] = "menu"

        await message.reply(
            "✅ **Post Saved!**\n\n"
            "Ab button add karo ya preview dekho.",
            reply_markup=post_menu_keyboard()
        )

        return


    # =====================================================
    # BUTTON NAME
    # =====================================================

    if step == "button_name":

        if not message.text:
            return await message.reply(
                "❌ Button ka naam text me bhejo."
            )

        custom_emoji_id = get_custom_emoji_id(
            message
        )

        session["current_button"] = {
            "text": message.text.strip(),
            "url": None,
            "style": None,
            "icon_custom_emoji_id": custom_emoji_id
        }

        session["step"] = "button_url"

        emoji_status = ""

        if custom_emoji_id:
            emoji_status = (
                "\n\n✨ Premium/Custom emoji detected!"
            )

        await message.reply(
            "🔗 **Button URL bhejo**\n\n"
            "Example:\n"
            "`https://t.me/yourchannel`"
            + emoji_status
        )

        return


    # =====================================================
    # BUTTON URL
    # =====================================================

    if step == "button_url":

        if not message.text:
            return

        url = message.text.strip()

        if not (
            url.startswith("https://")
            or url.startswith("http://")
            or url.startswith("tg://")
        ):

            return await message.reply(
                "❌ Invalid URL.\n\n"
                "URL `https://`, `http://` "
                "ya `tg://` se start honi chahiye."
            )

        current_button = session.get(
            "current_button"
        )

        if not current_button:
            return

        current_button["url"] = url

        session["step"] = "button_color"

        await message.reply(
            "🎨 **Button ka colour select karo:**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔵 Blue",
                            callback_data="post_color_primary"
                        ),
                        InlineKeyboardButton(
                            "🟢 Green",
                            callback_data="post_color_success"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔴 Red",
                            callback_data="post_color_danger"
                        ),
                        InlineKeyboardButton(
                            "⚪ Normal",
                            callback_data="post_color_default"
                        )
                    ]
                ]
            )
        )

        return


    # =====================================================
    # TARGET CHAT
    # =====================================================

    if step == "target":

        if not message.text:
            return

        target = message.text.strip()

        if target.lower() == "me":

            chat_id = user_id

        else:

            try:
                chat_id = int(target)

            except ValueError:

                # username support
                if target.startswith("@"):
                    chat_id = target

                else:
                    return await message.reply(
                        "❌ Invalid Chat ID.\n\n"
                        "Example:\n"
                        "`-1001234567890`\n\n"
                        "Ya:\n"
                        "`@channelusername`\n\n"
                        "Khud ko bhejne ke liye `me`."
                    )

        try:

            await send_post_via_bot_api(
                chat_id=chat_id,
                session=session
            )

            POST_SESSIONS.pop(
                user_id,
                None
            )

            await message.reply(
                "✅ **Post successfully sent!**"
            )

        except Exception as e:

            logger.exception(
                "Post send failed"
            )

            await message.reply(
                "❌ **Post send nahi hua.**\n\n"
                f"`{e}`"
            )

        return


# =========================================================
# ADD BUTTON
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^post_add_button$")
)
async def post_add_button(
    client: Bot,
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:

        return await callback.answer(
            "Session expired.",
            show_alert=True
        )

    session["step"] = "button_name"

    await callback.answer()

    await callback.message.edit_text(
        "🔘 **Button ka naam bhejo**\n\n"

        "Normal emoji ya Telegram Premium "
        "custom emoji bhi use kar sakte ho.\n\n"

        "Example:\n"
        "`Clon Tools ⚡`"
    )


# =========================================================
# BUTTON COLOR
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^post_color_")
)
async def post_button_color(
    client: Bot,
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:

        return await callback.answer(
            "Session expired.",
            show_alert=True
        )

    current_button = session.get(
        "current_button"
    )

    if not current_button:

        return await callback.answer(
            "Button data missing.",
            show_alert=True
        )

    color = callback.data.replace(
        "post_color_",
        ""
    )

    if color == "default":
        current_button["style"] = None

    else:
        current_button["style"] = color

    session["step"] = "button_layout"

    await callback.answer()

    # First button
    if not session["button_rows"]:

        session["button_rows"].append(
            [current_button]
        )

        session["current_button"] = None
        session["step"] = "menu"

        await callback.message.edit_text(
            "✅ **Button Added!**\n\n"
            "📐 Row: `1`\n"
            "🔘 Position: `1`\n\n"
            "Ab kya karna hai?",
            reply_markup=post_menu_keyboard()
        )

        return

    # Other buttons
    await callback.message.edit_text(
        "📐 **Button kaha rakhna hai?**\n\n"

        "🆕 **New Row**\n"
        "Button alag full-width line me aayega.\n\n"

        "↔️ **Same Row**\n"
        "Pichle button ke saath same line me aayega.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🆕 New Row",
                        callback_data="post_layout_new"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "↔️ Same Row",
                        callback_data="post_layout_same"
                    )
                ]
            ]
        )
    )


# =========================================================
# BUTTON LAYOUT
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^post_layout_")
)
async def post_button_layout(
    client: Bot,
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:

        return await callback.answer(
            "Session expired.",
            show_alert=True
        )

    current_button = session.get(
        "current_button"
    )

    if not current_button:

        return await callback.answer(
            "Button missing.",
            show_alert=True
        )

    layout = callback.data.replace(
        "post_layout_",
        ""
    )

    rows = session["button_rows"]

    if layout == "same":

        if not rows:

            rows.append(
                [current_button]
            )

        else:

            # Keep max 2 buttons in one row
            # for cleaner layout
            if len(rows[-1]) >= 2:

                rows.append(
                    [current_button]
                )

            else:

                rows[-1].append(
                    current_button
                )

    else:

        rows.append(
            [current_button]
        )

    session["current_button"] = None
    session["step"] = "menu"

    total_buttons = sum(
        len(row)
        for row in rows
    )

    await callback.answer(
        "Button added ✅"
    )

    await callback.message.edit_text(
        "✅ **Button Added!**\n\n"

        f"🔘 Total Buttons: `{total_buttons}`\n"
        f"📐 Total Rows: `{len(rows)}`\n\n"

        "Ab kya karna hai?",
        reply_markup=post_menu_keyboard()
    )


# =========================================================
# BUILD RAW INLINE KEYBOARD
# =========================================================

def build_inline_keyboard(session):

    inline_keyboard = []

    for row in session.get(
        "button_rows",
        []
    ):

        api_row = []

        for button in row:

            button_data = {
                "text": button["text"],
                "url": button["url"]
            }

            style = button.get("style")

            if style:
                button_data["style"] = style

            custom_emoji_id = button.get(
                "icon_custom_emoji_id"
            )

            if custom_emoji_id:

                button_data[
                    "icon_custom_emoji_id"
                ] = custom_emoji_id

            api_row.append(
                button_data
            )

        if api_row:
            inline_keyboard.append(
                api_row
            )

    return inline_keyboard


# =========================================================
# RAW TELEGRAM BOT API REQUEST
# =========================================================

async def telegram_api_request(
    method,
    payload
):

    api_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    async with aiohttp.ClientSession() as http:

        async with http.post(
            api_url,
            json=payload
        ) as response:

            result = await response.json()

            if not result.get("ok"):

                raise RuntimeError(
                    result.get(
                        "description",
                        "Telegram API Error"
                    )
                )

            return result


# =========================================================
# SEND POST
# =========================================================

async def send_post_via_bot_api(
    chat_id,
    session
):

    post_type = session.get("type")
    text = session.get("text") or ""
    file_id = session.get("file_id")

    inline_keyboard = build_inline_keyboard(
        session
    )

    reply_markup = None

    if inline_keyboard:

        reply_markup = {
            "inline_keyboard": inline_keyboard
        }


    # =====================================================
    # TEXT
    # =====================================================

    if post_type == "text":

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {
                "is_disabled": True
            }
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup

        return await telegram_api_request(
            "sendMessage",
            payload
        )


    # =====================================================
    # PHOTO
    # =====================================================

    if post_type == "photo":

        payload = {
            "chat_id": chat_id,
            "photo": file_id
        }

        if text:

            payload["caption"] = text
            payload["parse_mode"] = "HTML"

        if reply_markup:
            payload["reply_markup"] = reply_markup

        return await telegram_api_request(
            "sendPhoto",
            payload
        )


    # =====================================================
    # VIDEO
    # =====================================================

    if post_type == "video":

        payload = {
            "chat_id": chat_id,
            "video": file_id,
            "supports_streaming": True
        }

        if text:

            payload["caption"] = text
            payload["parse_mode"] = "HTML"

        if reply_markup:
            payload["reply_markup"] = reply_markup

        return await telegram_api_request(
            "sendVideo",
            payload
        )

    raise RuntimeError(
        "Unknown post type."
    )


# =========================================================
# PREVIEW
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^post_preview$")
)
async def post_preview(
    client: Bot,
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:

        return await callback.answer(
            "Session expired.",
            show_alert=True
        )

    await callback.answer()

    try:

        await send_post_via_bot_api(
            chat_id=user_id,
            session=session
        )

        await callback.message.reply(
            "👆 **Post Preview**\n\n"
            "Sahi hai to Send Post dabao.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📤 Send Post",
                            callback_data="post_send"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "➕ Add Button",
                            callback_data="post_add_button"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Cancel",
                            callback_data="post_cancel"
                        )
                    ]
                ]
            )
        )

    except Exception as e:

        logger.exception(
            "Preview failed"
        )

        await callback.message.reply(
            "❌ **Preview failed:**\n"
            f"`{e}`"
        )


# =========================================================
# SEND POST CALLBACK
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^post_send$")
)
async def post_send(
    client: Bot,
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:

        return await callback.answer(
            "Session expired.",
            show_alert=True
        )

    session["step"] = "target"

    await callback.answer()

    await callback.message.reply(
        "📤 **Post kaha send karna hai?**\n\n"

        "Channel/Group Chat ID:\n"
        "`-1001234567890`\n\n"

        "Public channel:\n"
        "`@channelusername`\n\n"

        "Khud ko bhejne ke liye:\n"
        "`me`\n\n"

        "⚠️ Channel/Group me bot ke paas "
        "required permission honi chahiye."
    )


# =========================================================
# CANCEL CALLBACK
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^post_cancel$")
)
async def post_cancel(
    client: Bot,
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    POST_SESSIONS.pop(
        user_id,
        None
    )

    await callback.answer(
        "Cancelled"
    )

    try:

        await callback.message.edit_text(
            "❌ **Post Creator Cancelled.**"
        )

    except Exception:

        await callback.message.reply(
            "❌ **Post Creator Cancelled.**"
        )


# =========================================================
# CLOSE ADMIN
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^admin_close$")
)
async def admin_close(
    client: Bot,
    callback: CallbackQuery
):

    if not is_owner(
        callback.from_user.id
    ):
        return

    await callback.answer()

    try:
        await callback.message.delete()

    except Exception:
        pass