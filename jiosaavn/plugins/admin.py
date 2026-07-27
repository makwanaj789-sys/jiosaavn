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
    return bool(user_id and OWNER_ID and user_id == OWNER_ID)


def is_post_creator_active(user_id: int) -> bool:
    return user_id in POST_SESSIONS


# =========================================================
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_refresh")],
        [InlineKeyboardButton("📝 Create Post", callback_data="admin_create_post")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ])


def total_buttons(session):
    return sum(len(row) for row in session.get("button_rows", []))


def post_menu_keyboard(session=None):
    keyboard = [[InlineKeyboardButton("➕ Add Button", callback_data="post_add_button")]]

    if session and total_buttons(session) > 0:
        keyboard.append([
            InlineKeyboardButton("✏️ Edit Buttons", callback_data="post_edit_buttons")
        ])

    keyboard.extend([
        [InlineKeyboardButton("👀 Preview", callback_data="post_preview")],
        [InlineKeyboardButton("❌ Cancel", callback_data="post_cancel")]
    ])

    return InlineKeyboardMarkup(keyboard)


async def get_admin_panel_text(client: Bot):
    stats = await client.db.get_admin_stats()

    return (
        "👑 **AARTI MUSIC • ADMIN PANEL**\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👥 **USERS & GROUPS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 **Total Users:** `{stats.get('total_users', 0):,}`\n"
        f"👥 **Total Groups:** `{stats.get('total_groups', 0):,}`\n"
        f"🟢 **Active Today:** `{stats.get('active_today', 0):,}`\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎵 **MUSIC ANALYTICS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🔎 **Total Searches:** `{stats.get('total_searches', 0):,}`\n"
        f"📅 **Today's Searches:** `{stats.get('searches_today', 0):,}`"
    )


@Bot.on_message(filters.command("admin") & filters.private)
async def admin_panel(client: Bot, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    try:
        text = await get_admin_panel_text(client)
        await message.reply(text, reply_markup=admin_keyboard())
    except Exception as e:
        logger.exception("Admin panel error")
        await message.reply(
            "❌ Admin panel error:\n"
            f"`{type(e).__name__}: {e}`"
        )


@Bot.on_callback_query(filters.regex(r"^admin_refresh$"))
async def admin_refresh(client: Bot, callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return await callback.answer("Not allowed.", show_alert=True)

    try:
        text = await get_admin_panel_text(client)
        await callback.message.edit_text(text, reply_markup=admin_keyboard())
        await callback.answer("Updated ✅")
    except Exception:
        logger.exception("Stats refresh error")
        await callback.answer("Refresh failed.", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^admin_create_post$"))
async def create_post(client: Bot, callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return await callback.answer("Not allowed.", show_alert=True)

    user_id = callback.from_user.id
    POST_SESSIONS[user_id] = {
        "step": "message",
        "type": None,
        "text": None,
        "file_id": None,
        "button_rows": [],
        "current_button": None,
        "editing_row": None,
        "editing_col": None
    }

    await callback.answer()
    await callback.message.edit_text(
        "📝 **AARTI POST CREATOR**\n\n"
        "Ab apna post bhejo.\n\n"
        "Supported:\n"
        "📝 Text Message\n"
        "🖼 Photo\n"
        "🎬 Video\n\n"
        "Media ke saath caption optional hai.\n\n"
        "❌ Cancel karne ke liye /cancel"
    )


@Bot.on_message(filters.command("cancel") & filters.private)
async def cancel_creator(client: Bot, message: Message):
    if not message.from_user or not is_owner(message.from_user.id):
        return

    POST_SESSIONS.pop(message.from_user.id, None)
    await message.reply("❌ Post Creator cancelled.")


# =========================================================
# SAFE UTF-16 / CUSTOM EMOJI
# =========================================================

def utf16_to_python_index(text: str, utf16_offset: int) -> int:
    """
    Telegram entity offsets are UTF-16 code units.
    Convert them without slicing/decoding partial surrogate pairs.
    """
    if utf16_offset <= 0:
        return 0

    units = 0
    for index, char in enumerate(text):
        char_units = 2 if ord(char) > 0xFFFF else 1

        if units == utf16_offset:
            return index

        if units + char_units > utf16_offset:
            # Offset unexpectedly lands inside a surrogate pair.
            # Returning the character boundary keeps slicing safe.
            return index

        units += char_units

    return len(text)


def extract_button_custom_emoji(message: Message):
    """
    Returns:
      clean button text
      first Telegram custom/premium emoji ID

    The visible fallback character belonging to a custom emoji entity
    is removed because the button uses icon_custom_emoji_id separately.
    """
    original_text = message.text or ""

    if not original_text:
        return "", None

    custom_ranges = []
    custom_emoji_id = None

    for entity in (message.entities or []):
        entity_type = getattr(entity, "type", None)
        name = getattr(entity_type, "name", None)

        if name:
            type_name = str(name).lower()
        else:
            type_name = str(entity_type or "").lower()

        if "custom_emoji" not in type_name:
            continue

        emoji_id = getattr(entity, "custom_emoji_id", None)
        if emoji_id and custom_emoji_id is None:
            custom_emoji_id = str(emoji_id)

        start = utf16_to_python_index(original_text, int(entity.offset))
        end = utf16_to_python_index(
            original_text,
            int(entity.offset) + int(entity.length)
        )

        if end < start:
            start, end = end, start

        custom_ranges.append((start, end))

    if not custom_ranges:
        return original_text.strip(), None

    clean_text = original_text

    # Remove ranges from right to left so previous indexes stay valid.
    for start, end in sorted(custom_ranges, key=lambda x: x[0], reverse=True):
        clean_text = clean_text[:start] + clean_text[end:]

    clean_text = " ".join(clean_text.split())

    # Telegram button text cannot be empty.
    if not clean_text:
        clean_text = "\u2063"

    return clean_text, custom_emoji_id


def get_editing_button(session):
    row_index = session.get("editing_row")
    col_index = session.get("editing_col")

    if row_index is None or col_index is None:
        return None

    rows = session.get("button_rows", [])

    if row_index < 0 or row_index >= len(rows):
        return None

    if col_index < 0 or col_index >= len(rows[row_index]):
        return None

    return rows[row_index][col_index]


def edit_button_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Name / Emoji", callback_data="post_edit_name")],
        [
            InlineKeyboardButton("🔗 URL", callback_data="post_edit_url"),
            InlineKeyboardButton("🎨 Colour", callback_data="post_edit_color")
        ],
        [InlineKeyboardButton("📐 Move / Layout", callback_data="post_edit_layout")],
        [InlineKeyboardButton("🗑 Delete Button", callback_data="post_edit_delete")],
        [InlineKeyboardButton("⬅️ Back", callback_data="post_edit_buttons")]
    ])


@Bot.on_message(
    filters.private
    & (filters.text | filters.photo | filters.video)
    & ~filters.command([
        "admin", "cancel", "start", "settings", "help", "about"
    ]),
    group=-5
)
async def post_creator_input(client: Bot, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    step = session.get("step")

    if step == "message":
        if message.text:
            session["type"] = "text"
            session["text"] = message.text
            session["file_id"] = None
        elif message.photo:
            session["type"] = "photo"
            session["text"] = message.caption or ""
            session["file_id"] = message.photo.file_id
        elif message.video:
            session["type"] = "video"
            session["text"] = message.caption or ""
            session["file_id"] = message.video.file_id
        else:
            return await message.reply("❌ Unsupported media.")

        session["step"] = "menu"

        await message.reply(
            "✅ **Post Saved!**\n\n"
            "Ab button add karo ya preview dekho.",
            reply_markup=post_menu_keyboard(session)
        )
        return

    if step == "button_name":
        if not message.text:
            return await message.reply("❌ Button ka naam text me bhejo.")

        button_text, custom_emoji_id = extract_button_custom_emoji(message)

        session["current_button"] = {
            "text": button_text,
            "url": None,
            "style": None,
            "icon_custom_emoji_id": custom_emoji_id
        }
        session["step"] = "button_url"

        if custom_emoji_id:
            await message.reply(
                "🔗 **Button URL bhejo**\n\n"
                "✨ Premium/Custom emoji detected!\n\n"
                "Premium emoji button icon me use hoga.\n\n"
                "Example:\n"
                "`https://t.me/yourchannel`"
            )
        else:
            await message.reply(
                "🔗 **Button URL bhejo**\n\n"
                "Example:\n"
                "`https://t.me/yourchannel`"
            )
        return

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
                "URL `https://`, `http://` ya `tg://` se start honi chahiye."
            )

        current_button = session.get("current_button")

        if not current_button:
            return await message.reply("❌ Button data missing.")

        current_button["url"] = url
        session["step"] = "button_color"

        await message.reply(
            "🎨 **Button ka colour select karo:**",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔵 Blue", callback_data="post_color_primary"),
                    InlineKeyboardButton("🟢 Green", callback_data="post_color_success")
                ],
                [
                    InlineKeyboardButton("🔴 Red", callback_data="post_color_danger"),
                    InlineKeyboardButton("⚪ Normal", callback_data="post_color_default")
                ]
            ])
        )
        return

    if step == "edit_name_input":
        if not message.text:
            return await message.reply("❌ Button ka naam text me bhejo.")

        button = get_editing_button(session)

        if not button:
            session["step"] = "menu"
            return await message.reply(
                "❌ Button nahi mila.",
                reply_markup=post_menu_keyboard(session)
            )

        button_text, custom_emoji_id = extract_button_custom_emoji(message)

        # Complete replacement:
        # premium -> premium = new ID
        # normal -> premium = new ID
        # premium -> normal = None
        button["text"] = button_text
        button["icon_custom_emoji_id"] = custom_emoji_id

        session["step"] = "edit_menu"

        if custom_emoji_id:
            status_text = (
                "✅ **Button name updated!**\n\n"
                "✨ Premium/Custom emoji detected.\n"
                "Premium emoji button icon me use hoga."
            )
        else:
            status_text = (
                "✅ **Button name updated!**\n\n"
                "🔘 Normal button text saved."
            )

        await message.reply(status_text, reply_markup=edit_button_menu())
        return

    if step == "edit_url_input":
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
                "`https://`, `http://` ya `tg://` se start karo."
            )

        button = get_editing_button(session)

        if not button:
            session["step"] = "menu"
            return await message.reply("❌ Button nahi mila.")

        button["url"] = url
        session["step"] = "edit_menu"

        await message.reply(
            "✅ **Button URL updated!**",
            reply_markup=edit_button_menu()
        )
        return

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
                if target.startswith("@"):
                    chat_id = target
                else:
                    return await message.reply(
                        "❌ Invalid Chat ID.\n\n"
                        "Example:\n"
                        "`-1001234567890`\n\n"
                        "Public channel:\n"
                        "`@channelusername`\n\n"
                        "Ya `me` bhejo."
                    )

        try:
            await send_post_via_bot_api(chat_id=chat_id, session=session)
            POST_SESSIONS.pop(user_id, None)
            await message.reply("✅ **Post successfully sent!**")
        except Exception as e:
            logger.exception("Post send failed")
            await message.reply(
                "❌ **Post send nahi hua.**\n\n"
                f"`{e}`"
            )
        return


@Bot.on_callback_query(filters.regex(r"^post_add_button$"))
async def post_add_button(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return await callback.answer("Session expired.", show_alert=True)

    session["step"] = "button_name"
    await callback.answer()

    try:
        await callback.message.edit_text(
            "🔘 **Button ka naam bhejo**\n\n"
            "Normal emoji ya Telegram Premium custom emoji bhi use kar sakte ho.\n\n"
            "Example:\n"
            "`Clon Tools ⚡`"
        )
    except Exception:
        await callback.message.reply("🔘 **Button ka naam bhejo**")


@Bot.on_callback_query(filters.regex(r"^post_color_"))
async def post_button_color(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return await callback.answer("Session expired.", show_alert=True)

    current_button = session.get("current_button")

    if not current_button:
        return await callback.answer("Button data missing.", show_alert=True)

    color = callback.data.replace("post_color_", "")

    current_button["style"] = None if color == "default" else color
    await callback.answer()

    if not session["button_rows"]:
        session["button_rows"].append([current_button])
        session["current_button"] = None
        session["step"] = "menu"

        await callback.message.edit_text(
            "✅ **Button Added!**\n\n"
            "📐 Row: `1`\n"
            "🔘 Position: `1`\n\n"
            "Ab kya karna hai?",
            reply_markup=post_menu_keyboard(session)
        )
        return

    session["step"] = "button_layout"

    await callback.message.edit_text(
        "📐 **Button kaha rakhna hai?**\n\n"
        "🆕 **New Row** — alag line\n\n"
        "↔️ **Same Row** — pichle button ke saath",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆕 New Row", callback_data="post_layout_new")],
            [InlineKeyboardButton("↔️ Same Row", callback_data="post_layout_same")]
        ])
    )


@Bot.on_callback_query(filters.regex(r"^post_layout_"))
async def post_button_layout(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return await callback.answer("Session expired.", show_alert=True)

    current_button = session.get("current_button")

    if not current_button:
        return await callback.answer("Button missing.", show_alert=True)

    layout = callback.data.replace("post_layout_", "")
    rows = session["button_rows"]

    if layout == "same":
        if not rows:
            rows.append([current_button])
        elif len(rows[-1]) >= 2:
            rows.append([current_button])
        else:
            rows[-1].append(current_button)
    else:
        rows.append([current_button])

    session["current_button"] = None
    session["step"] = "menu"

    await callback.answer("Button added ✅")
    await callback.message.edit_text(
        "✅ **Button Added!**\n\n"
        f"🔘 Total Buttons: `{total_buttons(session)}`\n"
        f"📐 Total Rows: `{len(rows)}`\n\n"
        "Ab kya karna hai?",
        reply_markup=post_menu_keyboard(session)
    )


@Bot.on_callback_query(filters.regex(r"^post_edit_buttons$"))
async def post_edit_buttons(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return await callback.answer("Session expired.", show_alert=True)

    rows = session.get("button_rows", [])

    if not rows:
        return await callback.answer("Koi button nahi hai.", show_alert=True)

    keyboard = []

    for row_index, row in enumerate(rows):
        for col_index, button in enumerate(row):
            name = button.get("text", "Button")

            if len(name) > 25:
                name = name[:22] + "..."

            keyboard.append([
                InlineKeyboardButton(
                    f"✏️ R{row_index + 1} • {name}",
                    callback_data=f"post_select_edit_{row_index}_{col_index}"
                )
            ])

    keyboard.append([
        InlineKeyboardButton("⬅️ Back", callback_data="post_back_menu")
    ])

    await callback.answer()
    await callback.message.edit_text(
        "✏️ **EDIT BUTTONS**\n\n"
        "Jis button ko edit karna hai use select karo:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@Bot.on_callback_query(filters.regex(r"^post_select_edit_"))
async def post_select_edit(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return await callback.answer("Session expired.", show_alert=True)

    try:
        data = callback.data.replace("post_select_edit_", "")
        row_index, col_index = map(int, data.split("_"))
        button = session["button_rows"][row_index][col_index]
    except Exception:
        return await callback.answer("Button nahi mila.", show_alert=True)

    session["editing_row"] = row_index
    session["editing_col"] = col_index
    session["step"] = "edit_menu"

    style = button.get("style") or "Normal"

    await callback.answer()
    await callback.message.edit_text(
        "✏️ **EDIT BUTTON**\n\n"
        f"🔘 Name: `{button.get('text', '')}`\n"
        f"🔗 URL: `{button.get('url', '')}`\n"
        f"🎨 Colour: `{style}`\n"
        f"📐 Row: `{row_index + 1}`\n"
        f"📍 Position: `{col_index + 1}`\n\n"
        "Kya edit karna hai?",
        reply_markup=edit_button_menu()
    )


@Bot.on_callback_query(filters.regex(r"^post_edit_name$"))
async def post_edit_name(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    session["step"] = "edit_name_input"
    await callback.answer()

    await callback.message.edit_text(
        "✏️ **Naya button name bhejo**\n\n"
        "Premium/Custom emoji bhi bhej sakte ho."
    )


@Bot.on_callback_query(filters.regex(r"^post_edit_url$"))
async def post_edit_url(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    session["step"] = "edit_url_input"
    await callback.answer()

    await callback.message.edit_text(
        "🔗 **Naya URL bhejo**\n\n"
        "Example:\n"
        "`https://t.me/yourchannel`"
    )


@Bot.on_callback_query(filters.regex(r"^post_edit_color$"))
async def post_edit_color(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    await callback.answer()

    await callback.message.edit_text(
        "🎨 **Naya button colour select karo:**",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔵 Blue", callback_data="post_set_edit_color_primary"),
                InlineKeyboardButton("🟢 Green", callback_data="post_set_edit_color_success")
            ],
            [
                InlineKeyboardButton("🔴 Red", callback_data="post_set_edit_color_danger"),
                InlineKeyboardButton("⚪ Normal", callback_data="post_set_edit_color_default")
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="post_edit_current_back")
            ]
        ])
    )


@Bot.on_callback_query(filters.regex(r"^post_set_edit_color_"))
async def post_set_edit_color(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    button = get_editing_button(session)

    if not button:
        return await callback.answer("Button nahi mila.", show_alert=True)

    color = callback.data.replace("post_set_edit_color_", "")
    button["style"] = None if color == "default" else color

    session["step"] = "edit_menu"

    await callback.answer("Colour updated ✅")
    await callback.message.edit_text(
        "✅ **Button colour updated!**\n\n"
        "Aur kuch edit karna hai?",
        reply_markup=edit_button_menu()
    )


@Bot.on_callback_query(filters.regex(r"^post_edit_layout$"))
async def post_edit_layout(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    await callback.answer()

    await callback.message.edit_text(
        "📐 **BUTTON POSITION**\n\n"
        "Button ko kaha move karna hai?\n\n"
        "⬆️ Previous Row\n"
        "⬇️ Next Row\n"
        "↔️ Previous button ke saath same row\n\n"
        "Maximum 2 buttons ek row me rakhe jayenge.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬆️ Previous Row", callback_data="post_move_previous")],
            [InlineKeyboardButton("⬇️ Next Row", callback_data="post_move_next")],
            [InlineKeyboardButton("↔️ Same With Previous", callback_data="post_move_same_previous")],
            [InlineKeyboardButton("⬅️ Back", callback_data="post_edit_current_back")]
        ])
    )


def remove_empty_rows(session):
    session["button_rows"] = [
        row for row in session.get("button_rows", []) if row
    ]


@Bot.on_callback_query(filters.regex(r"^post_move_previous$"))
async def post_move_previous(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    row_index = session.get("editing_row")
    col_index = session.get("editing_col")

    if row_index is None or col_index is None:
        return

    if row_index <= 0:
        return await callback.answer(
            "Ye already first row me hai.",
            show_alert=True
        )

    button = session["button_rows"][row_index].pop(col_index)
    session["button_rows"].insert(row_index - 1, [button])

    remove_empty_rows(session)

    session["editing_row"] = None
    session["editing_col"] = None
    session["step"] = "menu"

    await callback.answer("Button moved ✅")
    await callback.message.edit_text(
        "✅ **Button previous row me move ho gaya.**",
        reply_markup=post_menu_keyboard(session)
    )


@Bot.on_callback_query(filters.regex(r"^post_move_next$"))
async def post_move_next(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    row_index = session.get("editing_row")
    col_index = session.get("editing_col")

    if row_index is None or col_index is None:
        return

    rows = session["button_rows"]
    button = rows[row_index].pop(col_index)

    remove_empty_rows(session)

    new_index = min(row_index + 1, len(session["button_rows"]))
    session["button_rows"].insert(new_index, [button])

    session["editing_row"] = None
    session["editing_col"] = None
    session["step"] = "menu"

    await callback.answer("Button moved ✅")
    await callback.message.edit_text(
        "✅ **Button next row me move ho gaya.**",
        reply_markup=post_menu_keyboard(session)
    )


@Bot.on_callback_query(filters.regex(r"^post_move_same_previous$"))
async def post_move_same_previous(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    row_index = session.get("editing_row")
    col_index = session.get("editing_col")

    if row_index is None or col_index is None:
        return

    if row_index <= 0:
        return await callback.answer(
            "Previous row available nahi hai.",
            show_alert=True
        )

    rows = session["button_rows"]
    previous_row = rows[row_index - 1]

    if len(previous_row) >= 2:
        return await callback.answer(
            "Previous row me already 2 buttons hain.",
            show_alert=True
        )

    button = rows[row_index].pop(col_index)
    previous_row.append(button)

    remove_empty_rows(session)

    session["editing_row"] = None
    session["editing_col"] = None
    session["step"] = "menu"

    await callback.answer("Layout updated ✅")
    await callback.message.edit_text(
        "✅ **Button previous button ke saath same row me aa gaya.**",
        reply_markup=post_menu_keyboard(session)
    )


@Bot.on_callback_query(filters.regex(r"^post_edit_delete$"))
async def post_edit_delete(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    button = get_editing_button(session)

    if not button:
        return await callback.answer("Button nahi mila.", show_alert=True)

    name = button.get("text", "Button")

    await callback.answer()
    await callback.message.edit_text(
        "⚠️ **DELETE BUTTON?**\n\n"
        f"🔘 `{name}`\n\n"
        "Ye button permanently remove ho jayega.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Yes, Delete", callback_data="post_confirm_delete")],
            [InlineKeyboardButton("⬅️ No, Back", callback_data="post_edit_current_back")]
        ])
    )


@Bot.on_callback_query(filters.regex(r"^post_confirm_delete$"))
async def post_confirm_delete(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    row_index = session.get("editing_row")
    col_index = session.get("editing_col")

    try:
        session["button_rows"][row_index].pop(col_index)
    except Exception:
        return await callback.answer("Delete failed.", show_alert=True)

    remove_empty_rows(session)

    session["editing_row"] = None
    session["editing_col"] = None
    session["step"] = "menu"

    await callback.answer("Deleted ✅")
    await callback.message.edit_text(
        "🗑 **Button deleted!**\n\n"
        f"🔘 Remaining: `{total_buttons(session)}`",
        reply_markup=post_menu_keyboard(session)
    )


@Bot.on_callback_query(filters.regex(r"^post_edit_current_back$"))
async def post_edit_current_back(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    button = get_editing_button(session)

    if not button:
        return await callback.answer("Button missing.", show_alert=True)

    session["step"] = "edit_menu"

    await callback.answer()
    await callback.message.edit_text(
        "✏️ **EDIT BUTTON**\n\n"
        f"🔘 `{button.get('text', '')}`\n\n"
        "Kya edit karna hai?",
        reply_markup=edit_button_menu()
    )


@Bot.on_callback_query(filters.regex(r"^post_back_menu$"))
async def post_back_menu(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return

    session["step"] = "menu"
    session["editing_row"] = None
    session["editing_col"] = None

    await callback.answer()
    await callback.message.edit_text(
        "📝 **POST CREATOR**\n\n"
        f"🔘 Buttons: `{total_buttons(session)}`\n"
        f"📐 Rows: `{len(session['button_rows'])}`\n\n"
        "Ab kya karna hai?",
        reply_markup=post_menu_keyboard(session)
    )


def build_inline_keyboard(session):
    inline_keyboard = []

    for row in session.get("button_rows", []):
        api_row = []

        for button in row:
            button_data = {
                "text": button["text"],
                "url": button["url"]
            }

            style = button.get("style")
            if style:
                button_data["style"] = style

            custom_emoji_id = button.get("icon_custom_emoji_id")
            if custom_emoji_id:
                button_data["icon_custom_emoji_id"] = str(custom_emoji_id)

            api_row.append(button_data)

        if api_row:
            inline_keyboard.append(api_row)

    return inline_keyboard


async def telegram_api_request(method, payload):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    async with aiohttp.ClientSession() as http:
        async with http.post(api_url, json=payload) as response:
            result = await response.json()

            if not result.get("ok"):
                raise RuntimeError(
                    result.get("description", "Telegram API Error")
                )

            return result


async def send_post_via_bot_api(chat_id, session):
    post_type = session.get("type")
    text = session.get("text") or ""
    file_id = session.get("file_id")

    inline_keyboard = build_inline_keyboard(session)
    reply_markup = {"inline_keyboard": inline_keyboard} if inline_keyboard else None

    if post_type == "text":
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True}
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup

        return await telegram_api_request("sendMessage", payload)

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

        return await telegram_api_request("sendPhoto", payload)

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

        return await telegram_api_request("sendVideo", payload)

    raise RuntimeError("Unknown post type.")


@Bot.on_callback_query(filters.regex(r"^post_preview$"))
async def post_preview(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return await callback.answer("Session expired.", show_alert=True)

    await callback.answer()

    try:
        await send_post_via_bot_api(chat_id=user_id, session=session)

        keyboard = [
            [InlineKeyboardButton("📤 Send Post", callback_data="post_send")],
            [InlineKeyboardButton("➕ Add Button", callback_data="post_add_button")]
        ]

        if total_buttons(session) > 0:
            keyboard.append([
                InlineKeyboardButton("✏️ Edit Buttons", callback_data="post_edit_buttons")
            ])

        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="post_cancel")
        ])

        await callback.message.reply(
            "👆 **Post Preview**\n\n"
            "Sahi hai to Send Post dabao.\n"
            "Galti hai to Edit Buttons use karo.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.exception("Preview failed")
        await callback.message.reply(
            "❌ **Preview failed:**\n"
            f"`{e}`"
        )


@Bot.on_callback_query(filters.regex(r"^post_send$"))
async def post_send(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    session = POST_SESSIONS.get(user_id)

    if not session:
        return await callback.answer("Session expired.", show_alert=True)

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
        "⚠️ Channel/Group me bot ke paas required permissions honi chahiye."
    )


@Bot.on_callback_query(filters.regex(r"^post_cancel$"))
async def post_cancel(client: Bot, callback: CallbackQuery):
    user_id = callback.from_user.id

    if not is_owner(user_id):
        return

    POST_SESSIONS.pop(user_id, None)

    await callback.answer("Cancelled")

    try:
        await callback.message.edit_text("❌ **Post Creator Cancelled.**")
    except Exception:
        try:
            await callback.message.reply("❌ **Post Creator Cancelled.**")
        except Exception:
            pass


@Bot.on_callback_query(filters.regex(r"^admin_close$"))
async def admin_close(client: Bot, callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return

    await callback.answer()

    try:
        await callback.message.delete()
    except Exception:
        pass
