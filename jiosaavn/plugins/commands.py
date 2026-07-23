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


# ==================== START / HOME ====================

@Bot.on_callback_query(filters.regex(r"^home$"))
@Bot.on_message(filters.command("start") & filters.private)
async def start(client: Bot, message: Message | CallbackQuery):

    try:
        # Callback query
        if isinstance(message, CallbackQuery):
            user = message.from_user
            msg = message.message
            await message.answer()

        # Normal /start command
        else:
            user = message.from_user
            msg = None

        last_name = (
            f" {user.last_name}"
            if user.last_name
            else ""
        )

        mention = (
            f"[{user.first_name}{last_name}]"
            f"(tg://user?id={user.id})"
            if user.first_name
            else f"[User](tg://user?id={user.id})"
        )

        # If normal /start command
        if msg is None:
            msg = await message.reply(
                "**Processing....⌛**",
                quote=True
            )

        # Updated buttons
        buttons = [
            [
                InlineKeyboardButton(
                    "About 📕",
                    callback_data="about"
                ),
                InlineKeyboardButton(
                    "Help 💡",
                    callback_data="help"
                )
            ],
            [
                InlineKeyboardButton(
                    "Settings ⚙",
                    callback_data="settings"
                ),
                InlineKeyboardButton(
                    "Updates 📢",
                    url="https://t.me/umclon_era"
                )
            ],
            [
                InlineKeyboardButton(
                    "Owner 👑",
                    url="https://t.me/umclon"
                )
            ],
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]

        await msg.edit(
            text=TEXT.START_MSG.format(
                mention=mention
            ),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:

        logger.exception(
            f"Error inside /start handler: {e}"
        )

        try:
            if isinstance(message, CallbackQuery):
                await message.message.edit(
                    "❌ An error occurred while processing your request."
                )
            else:
                await message.reply(
                    "❌ An error occurred while processing your request."
                )
        except Exception:
            logger.exception(
                "Could not send start error message"
            )


# ==================== HELP ====================

@Bot.on_callback_query(filters.regex(r"^help$"))
@Bot.on_message(filters.command("help") & filters.private)
async def help_handler(
    client: Bot,
    message: Message | CallbackQuery
):

    try:

        if isinstance(message, CallbackQuery):
            await message.answer()
            msg = message.message

        else:
            msg = await message.reply(
                "**Processing-please wait....⌛**",
                quote=True
            )

        buttons = [
            [
                InlineKeyboardButton(
                    "About 📕",
                    callback_data="about"
                ),
                InlineKeyboardButton(
                    "Settings ⚙",
                    callback_data="settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "Updates 📢",
                    url="https://t.me/umclon_era"
                ),
                InlineKeyboardButton(
                    "Owner 👑",
                    url="https://t.me/umclon"
                )
            ],
            [
                InlineKeyboardButton(
                    "Home 🏕",
                    callback_data="home"
                ),
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]

        await msg.edit(
            text=TEXT.HELP_MSG,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

    except Exception as e:

        logger.exception(
            f"Error inside help_handler: {e}"
        )

        try:
            if isinstance(message, CallbackQuery):
                await message.message.edit(
                    "❌ An error occurred while processing your request."
                )
            else:
                await message.reply(
                    "❌ An error occurred while processing your request."
                )
        except Exception:
            logger.exception(
                "Could not send help error message"
            )


# ==================== ABOUT ====================

@Bot.on_callback_query(filters.regex(r"^about$"))
@Bot.on_message(filters.command("about") & filters.private)
async def about(
    client: Bot,
    message: Message | CallbackQuery
):

    try:

        if isinstance(message, CallbackQuery):
            await message.answer()
            msg = message.message

        else:
            msg = await message.reply(
                "**Processing-please wait....⌛**",
                quote=True
            )

        me = await client.get_me()

        buttons = [
            [
                InlineKeyboardButton(
                    "Help 💡",
                    callback_data="help"
                ),
                InlineKeyboardButton(
                    "Settings ⚙",
                    callback_data="settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "Updates 📢",
                    url="https://t.me/umclon_era"
                ),
                InlineKeyboardButton(
                    "Owner 👑",
                    url="https://t.me/umclon"
                )
            ],
            [
                InlineKeyboardButton(
                    "Home 🏕",
                    callback_data="home"
                ),
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]

        await msg.edit(
            text=TEXT.ABOUT_MSG.format(
                me=me
            ),
            reply_markup=InlineKeyboardMarkup(
                buttons
            ),
            disable_web_page_preview=True
        )

    except Exception as e:

        logger.exception(
            f"Error inside about handler: {e}"
        )

        try:
            if isinstance(message, CallbackQuery):
                await message.message.edit(
                    "❌ An error occurred while processing your request."
                )
            else:
                await message.reply(
                    "❌ An error occurred while processing your request."
                )
        except Exception:
            logger.exception(
                "Could not send about error message"
            )


# ==================== CLOSE ====================

@Bot.on_callback_query(filters.regex(r"^close$"))
async def close_cb(
    client: Bot,
    callback: CallbackQuery
):

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

        logger.exception(
            f"Error inside close callback: {e}"
        )