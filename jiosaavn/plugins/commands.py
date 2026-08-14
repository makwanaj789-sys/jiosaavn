import logging

from jiosaavn.bot import Bot
from jiosaavn.plugins.text import TEXT

from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

logger = logging.getLogger(__name__)


async def get_bot_photo(client: Bot):
    """
    Fetches the bot's own profile photo file_id so we can send it
    with the start message.
    """
    try:
        me = await client.get_me()
        if me.photo:
            return me.photo.big_file_id
    except Exception as e:
        logger.warning(f"Couldn't fetch bot photo: {e}")
    return None


# ==================== START / HOME ====================

@Bot.on_callback_query(filters.regex(r"^home$"))
@Bot.on_message(filters.command("start") & filters.private)
async def start(client: Bot, message: Message | CallbackQuery):

    try:
        is_callback = isinstance(message, CallbackQuery)

        if is_callback:
            user = message.from_user
            await message.answer()
        else:
            user = message.from_user

        last_name = f" {user.last_name}" if user.last_name else ""

        mention = (
            f"[{user.first_name}{last_name}](tg://user?id={user.id})"
            if user.first_name
            else f"[User](tg://user?id={user.id})"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➕ Add me to your group",
                    url="https://t.me/AartiMusic_bot?startgroup=true"
                )
            ],
            [
                InlineKeyboardButton("💡 Help", callback_data="help"),
                InlineKeyboardButton("📕 About", callback_data="about")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("📢 Updates", url="https://t.me/umclon_era")
            ],
            [
                InlineKeyboardButton("👑 Owner", url="https://t.me/umclon"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])

        caption = TEXT.START_MSG.format(mention=mention)
        photo_id = await get_bot_photo(client)

        # Coming back from another menu — edit the existing message
        if is_callback:
            try:
                if message.message.photo:
                    await message.message.edit_caption(
                        caption=caption,
                        reply_markup=buttons
                    )
                else:
                    await message.message.edit_text(
                        text=caption,
                        reply_markup=buttons,
                        disable_web_page_preview=True
                    )
            except Exception:
                pass
            return

        # Fresh /start — send the bot's photo with details below
        if photo_id:
            await message.reply_photo(
                photo=photo_id,
                caption=caption,
                reply_markup=buttons,
                quote=True
            )
        else:
            await message.reply(
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True,
                quote=True
            )

    except Exception as e:
        logger.exception(f"Error inside /start handler: {e}")
        try:
            if isinstance(message, CallbackQuery):
                await message.message.reply("❌ An error occurred while processing your request.")
            else:
                await message.reply("❌ An error occurred while processing your request.")
        except Exception:
            logger.exception("Could not send start error message")

@Bot.on_callback_query(filters.regex(r"^help$"))
@Bot.on_message(filters.command("help") & filters.private)
async def help_handler(client: Bot, message: Message | CallbackQuery):

    try:
        is_callback = isinstance(message, CallbackQuery)

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎵 Try inline search",
                    switch_inline_query_current_chat=""
                )
            ],
            [
                InlineKeyboardButton("📕 About", callback_data="about"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton("🏠 Home", callback_data="home"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])

        if is_callback:
            await message.answer()
            try:
                if message.message.photo:
                    await message.message.edit_caption(
                        caption=TEXT.HELP_MSG,
                        reply_markup=buttons
                    )
                else:
                    await message.message.edit_text(
                        text=TEXT.HELP_MSG,
                        reply_markup=buttons,
                        disable_web_page_preview=True
                    )
            except Exception:
                pass
        else:
            await message.reply(
                text=TEXT.HELP_MSG,
                reply_markup=buttons,
                disable_web_page_preview=True,
                quote=True
            )

    except Exception as e:
        logger.exception(f"Error inside help_handler: {e}")


@Bot.on_callback_query(filters.regex(r"^about$"))
@Bot.on_message(filters.command("about") & filters.private)
async def about(client: Bot, message: Message | CallbackQuery):

    try:
        is_callback = isinstance(message, CallbackQuery)
        me = await client.get_me()

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💡 Help", callback_data="help"),
                InlineKeyboardButton("📢 Updates", url="https://t.me/umclon_era")
            ],
            [
                InlineKeyboardButton("👑 Owner", url="https://t.me/umclon")
            ],
            [
                InlineKeyboardButton("🏠 Home", callback_data="home"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])

        caption = TEXT.ABOUT_MSG.format(me=me)

        if is_callback:
            await message.answer()
            try:
                if message.message.photo:
                    await message.message.edit_caption(
                        caption=caption,
                        reply_markup=buttons
                    )
                else:
                    await message.message.edit_text(
                        text=caption,
                        reply_markup=buttons,
                        disable_web_page_preview=True
                    )
            except Exception:
                pass
        else:
            await message.reply(
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True,
                quote=True
            )

    except Exception as e:
        logger.exception(f"Error inside about handler: {e}")

# ==================== CLOSE ====================

@Bot.on_callback_query(filters.regex(r"^close$"))
async def close_cb(client: Bot, callback: CallbackQuery):
    try:
        await callback.answer()

        reply_to = callback.message.reply_to_message
        await callback.message.delete()

        if reply_to:
            try:
                await reply_to.delete()
            except Exception:
                pass

    except Exception as e:
        logger.exception(f"Error inside close callback: {e}")