import os
import random
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

# Folder where start images live (repo_root/assets/start_images)
START_IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets",
    "start_images"
)

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def get_random_start_image():
    """
    Picks a random image from assets/start_images.
    Returns the filepath, or None if the folder is missing/empty.
    """
    try:
        if not os.path.isdir(START_IMAGES_DIR):
            logger.warning(f"Start images folder not found: {START_IMAGES_DIR}")
            return None

        images = [
            os.path.join(START_IMAGES_DIR, f)
            for f in os.listdir(START_IMAGES_DIR)
            if f.lower().endswith(VALID_EXTENSIONS)
        ]

        if not images:
            logger.warning("No images found in start_images folder")
            return None

        return random.choice(images)

    except Exception as e:
        logger.warning(f"get_random_start_image error: {e}")
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

        # Fresh /start — send a random image with details below
        image_path = get_random_start_image()

        if image_path:
            await message.reply_photo(
                photo=image_path,
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


# ==================== HELP ====================

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


# ==================== ABOUT ====================

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