import logging

from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from jiosaavn.bot import Bot
from jiosaavn.config.settings import OWNER_ID


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
# COMMON POST MENU
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
async def admin_panel(
    client: Bot,
    message: Message
):

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

        logger.exception(
            "Admin panel error"
        )

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
async def admin_refresh(
    client: Bot,
    callback: CallbackQuery
):

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

        await callback.answer(
            "Updated ✅"
        )

    except Exception:

        logger.exception(
            "Stats refresh error"
        )

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
async def create_post(
    client: Bot,
    callback: CallbackQuery
):

    if not is_owner(callback.from_user.id):

        return await callback.answer(
            "Not allowed.",
            show_alert=True
        )

    user_id = callback.from_user.id

    POST_SESSIONS[user_id] = {
        "step": "message",

        # Post type:
        # text / photo / video
        "type": None,

        # Text or media caption
        "text": None,

        # Telegram formatting entities
        "entities": None,

        # Telegram file_id for photo/video
        "file_id": None,

        # URL buttons
        "buttons": []
    }

    await callback.answer()

    await callback.message.edit_text(
        "📝 **AARTI POST CREATOR**\n\n"
        "Ab apna post bhejo.\n\n"
        "Supported:\n"
        "📝 Text Message\n"
        "🖼 Photo + Caption\n"
        "🎥 Video + Caption\n\n"
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
async def cancel_creator(
    client: Bot,
    message: Message
):

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
# POST INPUT HANDLER
#
# IMPORTANT:
# Text + Photo + Video tino accept honge.
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

        # ---------------------------------------------
        # VIDEO POST
        # ---------------------------------------------

        if message.video:

            session["type"] = "video"
            session["file_id"] = message.video.file_id

            session["text"] = (
                message.caption
                if message.caption
                else ""
            )

            session["entities"] = (
                message.caption_entities
                if message.caption_entities
                else None
            )

            saved_type = "🎥 Video"


        # ---------------------------------------------
        # PHOTO POST
        # ---------------------------------------------

        elif message.photo:

            session["type"] = "photo"

            # Highest available photo resolution
            session["file_id"] = message.photo.file_id

            session["text"] = (
                message.caption
                if message.caption
                else ""
            )

            session["entities"] = (
                message.caption_entities
                if message.caption_entities
                else None
            )

            saved_type = "🖼 Photo"


        # ---------------------------------------------
        # TEXT POST
        # ---------------------------------------------

        elif message.text:

            session["type"] = "text"
            session["file_id"] = None
            session["text"] = message.text

            session["entities"] = (
                message.entities
                if message.entities
                else None
            )

            saved_type = "📝 Message"

        else:
            return


        session["step"] = "menu"

        await message.reply(
            f"✅ **{saved_type} Saved!**\n\n"
            "Ab kya karna hai?",
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

        session["current_button"] = {
            "text": message.text.strip()
        }

        session["step"] = "button_url"

        await message.reply(
            "🔗 **Button URL bhejo**\n\n"
            "Example:\n"
            "`https://t.me/yourchannel`"
        )

        return


    # =====================================================
    # BUTTON URL
    # =====================================================

    if step == "button_url":

        if not message.text:
            return await message.reply(
                "❌ URL text me bhejo."
            )

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

        session["current_button"]["url"] = url

        session["step"] = "button_color"

        await message.reply(
            "🎨 **Button ka colour select karo:**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔵 Blue",
                            callback_data="post_color_primary"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🟢 Green",
                            callback_data="post_color_success"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔴 Red",
                            callback_data="post_color_danger"
                        )
                    ],
                    [
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
            return await message.reply(
                "❌ Chat ID text me bhejo."
            )

        target = message.text.strip()

        if target.lower() == "me":

            chat_id = user_id

        else:

            try:
                chat_id = int(target)

            except ValueError:

                return await message.reply(
                    "❌ Invalid Chat ID.\n\n"
                    "Example:\n"
                    "`-1001234567890`\n\n"
                    "Ya `me` bhejo."
                )

        try:

            await send_created_post(
                client=client,
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
                f"`{type(e).__name__}: {e}`"
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
        "Example:\n"
        "`Join Channel 📢`"
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

    session["buttons"].append(
        current_button
    )

    session.pop(
        "current_button",
        None
    )

    session["step"] = "menu"

    await callback.answer(
        "Button added ✅"
    )

    await callback.message.edit_text(
        "✅ **Button Added!**\n\n"
        f"🔘 Total Buttons: "
        f"`{len(session['buttons'])}`\n\n"
        "Ab kya karna hai?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ Add Another Button",
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
    )


# =========================================================
# BUILD INLINE KEYBOARD
# =========================================================

def build_post_keyboard(buttons):

    if not buttons:
        return None

    rows = []

    for button in buttons:

        kwargs = {
            "text": button["text"],
            "url": button["url"]
        }

        # Telegram/Pyrogram versions which support
        # styled buttons can use this.
        style = button.get("style")

        if style:
            kwargs["style"] = style

        try:

            btn = InlineKeyboardButton(
                **kwargs
            )

        except TypeError:

            # Compatibility fallback if current
            # Pyrogram version doesn't support style.
            kwargs.pop("style", None)

            btn = InlineKeyboardButton(
                **kwargs
            )

        rows.append([btn])

    return InlineKeyboardMarkup(rows)


# =========================================================
# SEND CREATED POST
# =========================================================

async def send_created_post(
    client: Bot,
    chat_id,
    session
):

    post_type = session.get("type")

    text = session.get("text") or ""

    file_id = session.get("file_id")

    entities = session.get("entities")

    keyboard = build_post_keyboard(
        session.get("buttons", [])
    )


    # =====================================================
    # TEXT
    # =====================================================

    if post_type == "text":

        if not text:
            raise ValueError(
                "Post text missing."
            )

        return await client.send_message(
            chat_id=chat_id,
            text=text,
            entities=entities,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )


    # =====================================================
    # PHOTO
    # =====================================================

    if post_type == "photo":

        if not file_id:
            raise ValueError(
                "Photo file_id missing."
            )

        return await client.send_photo(
            chat_id=chat_id,
            photo=file_id,
            caption=text if text else None,
            caption_entities=entities,
            reply_markup=keyboard
        )


    # =====================================================
    # VIDEO
    # =====================================================

    if post_type == "video":

        if not file_id:
            raise ValueError(
                "Video file_id missing."
            )

        return await client.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=text if text else None,
            caption_entities=entities,
            reply_markup=keyboard,
            supports_streaming=True
        )


    raise ValueError(
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

        # Actual post preview
        await send_created_post(
            client=client,
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
            "❌ Preview failed:\n"
            f"`{type(e).__name__}: {e}`"
        )


# =========================================================
# SEND POST
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
        "Channel/Group ka Chat ID bhejo.\n\n"
        "Example:\n"
        "`-1001234567890`\n\n"
        "Khud ko bhejne ke liye:\n"
        "`me`\n\n"
        "⚠️ Channel/Group me bot admin hona chahiye."
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