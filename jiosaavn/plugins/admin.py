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
# OWNER CHECK
# =========================================================

def is_owner(user_id: int) -> bool:
    """
    Check whether the user is the bot owner.
    """
    return bool(
        user_id
        and OWNER_ID
        and user_id == OWNER_ID
    )


# =========================================================
# ADMIN PANEL KEYBOARD
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

    total_users = stats.get(
        "total_users",
        0
    )

    total_groups = stats.get(
        "total_groups",
        0
    )

    total_searches = stats.get(
        "total_searches",
        0
    )

    searches_today = stats.get(
        "searches_today",
        0
    )

    active_today = stats.get(
        "active_today",
        0
    )

    text = (
        "👑 **AARTI MUSIC • ADMIN PANEL**\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "👥 **USERS & GROUPS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 **Total Users:** `{total_users:,}`\n"
        f"👥 **Total Groups:** `{total_groups:,}`\n"
        f"🟢 **Active Today:** `{active_today:,}`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🎵 **MUSIC ANALYTICS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🔎 **Total Searches:** `{total_searches:,}`\n"
        f"📅 **Today's Searches:** `{searches_today:,}`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "⚙️ **ADMIN TOOLS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "📝 Create posts with custom buttons.\n"
        "🔄 Refresh to get latest statistics."
    )

    return text


# =========================================================
# /ADMIN COMMAND
# =========================================================

@Bot.on_message(
    filters.command("admin")
    & filters.private
)
async def admin_panel(
    client: Bot,
    message: Message
):

    # -----------------------------------------------------
    # OWNER ONLY
    # -----------------------------------------------------

    if not message.from_user:
        return

    if not is_owner(
        message.from_user.id
    ):

        # Don't reveal admin functionality
        # to normal users.
        return

    try:

        text = await get_admin_panel_text(
            client
        )

        await message.reply(
            text,
            reply_markup=admin_keyboard()
        )

    except Exception as e:

        logger.exception(
            "Failed to open admin panel"
        )

        await message.reply(
            "❌ **Admin panel load nahi hua.**\n\n"
            f"`{type(e).__name__}: {e}`"
        )


# =========================================================
# REFRESH STATS
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^admin_refresh$")
)
async def admin_refresh(
    client: Bot,
    callback: CallbackQuery
):

    if not callback.from_user:
        return

    if not is_owner(
        callback.from_user.id
    ):

        return await callback.answer(
            "You are not allowed to use this.",
            show_alert=True
        )

    try:

        text = await get_admin_panel_text(
            client
        )

        await callback.message.edit_text(
            text,
            reply_markup=admin_keyboard()
        )

        await callback.answer(
            "Stats updated ✅"
        )

    except Exception as e:

        logger.exception(
            "Admin stats refresh failed"
        )

        await callback.answer(
            "Stats refresh failed.",
            show_alert=True
        )


# =========================================================
# CREATE POST BUTTON
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^admin_create_post$")
)
async def admin_create_post(
    client: Bot,
    callback: CallbackQuery
):

    if not callback.from_user:
        return

    if not is_owner(
        callback.from_user.id
    ):

        return await callback.answer(
            "You are not allowed to use this.",
            show_alert=True
        )

    await callback.answer()

    await callback.message.edit_text(
        "📝 **AARTI POST CREATOR**\n\n"
        "Post Creator ka button ready hai.\n\n"
        "Next step me isme ye options honge:\n\n"
        "• 📝 Message / Caption\n"
        "• 🔗 Custom URL Button\n"
        "• 🔵 Blue Button\n"
        "• 🟢 Green Button\n"
        "• 🔴 Red Button\n"
        "• ➕ Multiple Buttons\n"
        "• 👀 Preview\n"
        "• 📤 Send",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Back",
                        callback_data="admin_back"
                    )
                ]
            ]
        )
    )


# =========================================================
# BACK TO ADMIN
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^admin_back$")
)
async def admin_back(
    client: Bot,
    callback: CallbackQuery
):

    if not callback.from_user:
        return

    if not is_owner(
        callback.from_user.id
    ):

        return await callback.answer(
            "Not allowed.",
            show_alert=True
        )

    try:

        text = await get_admin_panel_text(
            client
        )

        await callback.message.edit_text(
            text,
            reply_markup=admin_keyboard()
        )

        await callback.answer()

    except Exception:

        logger.exception(
            "Failed to return to admin panel"
        )


# =========================================================
# CLOSE ADMIN PANEL
# =========================================================

@Bot.on_callback_query(
    filters.regex(r"^admin_close$")
)
async def admin_close(
    client: Bot,
    callback: CallbackQuery
):

    if not callback.from_user:
        return

    if not is_owner(
        callback.from_user.id
    ):

        return await callback.answer(
            "Not allowed.",
            show_alert=True
        )

    await callback.answer(
        "Admin panel closed."
    )

    try:
        await callback.message.delete()

    except Exception:
        logger.exception(
            "Failed to delete admin panel"
        )