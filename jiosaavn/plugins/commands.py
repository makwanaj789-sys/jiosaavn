import logging
import asyncio
import random

from jiosaavn.bot import Bot
from jiosaavn.plugins.text import TEXT

from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

logger = logging.getLogger(__name__)


# ==================== START / HOME ====================

@Bot.on_callback_query(filters.regex('^home$'))
@Bot.on_message(filters.command('start') & filters.private)
async def start(c, m):

    print("START DEBUG 1: /start handler triggered", flush=True)

    try:
        # Callback query me actual message yahan milega
        if isinstance(m, CallbackQuery):
            user = m.from_user
            msg = m.message
            await m.answer()
        else:
            user = m.from_user
            msg = None

        print(f"START DEBUG 2: user = {user.id}", flush=True)

        last_name = f" {user.last_name}" if user.last_name else ""

        mention = (
            f"[{user.first_name}{last_name}](tg://user?id={user.id})"
            if user.first_name
            else f"[User](tg://user?id={user.id})"
        )

        # /start command se aaya hai
        if msg is None:
            print(
                "START DEBUG 3: sending processing message",
                flush=True
            )

            msg = await m.reply(
                "**Processing....⌛**",
                quote=True
            )

            print(
                "START DEBUG 4: processing message sent",
                flush=True
            )

        buttons = [
            [
                InlineKeyboardButton(
                    "Owner 🧑",
                    url="https://t.me/The_proGrammerr"
                ),
                InlineKeyboardButton(
                    "About 📕",
                    callback_data="about"
                )
            ],
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
                    "Open Source Repository 🌐",
                    url="https://github.com/Ns-AnoNymouS/jiosaavn"
                )
            ],
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]

        print(
            "START DEBUG 5: editing message",
            flush=True
        )

        await msg.edit(
            text=TEXT.START_MSG.format(
                mention=mention
            ),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        print(
            "START DEBUG 6: /start completed successfully",
            flush=True
        )

    except Exception as e:

        print(
            f"START ERROR: {type(e).__name__}: {e}",
            flush=True
        )

        logger.exception(
            "Error inside /start handler"
        )

        try:
            if isinstance(m, CallbackQuery):
                await m.message.edit(
                    "An error occurred while processing your request."
                )
            else:
                await m.reply(
                    "An error occurred while processing your request."
                )
        except Exception:
            logger.exception(
                "Could not send start error message"
            )


# ==================== HELP ====================

@Bot.on_callback_query(filters.regex('^help$'))
@Bot.on_message(filters.command('help') & filters.private)
async def help_handler(
    client: Bot,
    message: Message | CallbackQuery
):

    print("HELP DEBUG: handler triggered", flush=True)

    try:

        if isinstance(message, CallbackQuery):
            await message.answer()
            msg = message.message
        else:
            msg = await message.reply(
                "**Processing....⌛**",
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
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        print(
            "HELP DEBUG: completed successfully",
            flush=True
        )

    except Exception as e:

        print(
            f"HELP ERROR: {type(e).__name__}: {e}",
            flush=True
        )

        logger.exception(
            "Error inside help_handler"
        )

        try:
            if isinstance(message, CallbackQuery):
                await message.message.edit(
                    "An error occurred while processing your request."
                )
            else:
                await message.reply(
                    "An error occurred while processing your request."
                )
        except Exception:
            pass


# ==================== ABOUT ====================

@Bot.on_callback_query(filters.regex('^about$'))
@Bot.on_message(filters.command('about') & filters.private)
async def about(
    client: Bot,
    message: Message | CallbackQuery
):

    print("ABOUT DEBUG: handler triggered", flush=True)

    try:

        if isinstance(message, CallbackQuery):
            await message.answer()
            msg = message.message
        else:
            msg = await message.reply(
                "**Processing....⌛**",
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
            text=TEXT.ABOUT_MSG.format(me=me),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

        print(
            "ABOUT DEBUG: completed successfully",
            flush=True
        )

    except Exception as e:

        print(
            f"ABOUT ERROR: {type(e).__name__}: {e}",
            flush=True
        )

        logger.exception(
            "Error inside about handler"
        )

        try:
            if isinstance(message, CallbackQuery):
                await message.message.edit(
                    "An error occurred while processing your request."
                )
            else:
                await message.reply(
                    "An error occurred while processing your request."
                )
        except Exception:
            pass


# ==================== CLOSE ====================

@Bot.on_callback_query(filters.regex('^close$'))
async def close_cb(
    client: Bot,
    callback: CallbackQuery
):

    print("CLOSE DEBUG: handler triggered", flush=True)

    try:

        await callback.answer()

        reply_to = callback.message.reply_to_message

        await callback.message.delete()

        if reply_to:
            try:
                await reply_to.delete()
            except Exception:
                pass

        print(
            "CLOSE DEBUG: completed successfully",
            flush=True
        )

    except Exception as e:

        print(
            f"CLOSE ERROR: {type(e).__name__}: {e}",
            flush=True
        )

        logger.exception(
            "Error inside close callback"
        )