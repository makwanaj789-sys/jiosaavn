import os
import logging
from pyrogram import filters, enums
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from jiosaavn.bot import Bot
from api.settings import SettingsManager
from api.settings_image import build_settings_card, SETTINGS_CARD_PATH

logger = logging.getLogger(__name__)


async def get_card(client: Bot):
    if os.path.exists(SETTINGS_CARD_PATH):
        return SETTINGS_CARD_PATH
    try:
        me = await client.get_me()
        if me.photo:
            pfp = await client.download_media(me.photo.big_file_id)
            card = build_settings_card(pfp)
            try:
                os.remove(pfp)
            except Exception:
                pass
            return card
    except Exception as e:
        logger.warning(f"get_card error: {e}")
    return None


def settings_markup(play_mode: str):
    admins_selected = play_mode == "admins"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{'✅ ' if admins_selected else ''}Admins Only",
                callback_data="set_mode_admins",
                style=enums.ButtonStyle.SUCCESS if admins_selected else enums.ButtonStyle.DEFAULT
            ),
            InlineKeyboardButton(
                f"{'✅ ' if not admins_selected else ''}Everyone",
                callback_data="set_mode_everyone",
                style=enums.ButtonStyle.SUCCESS if not admins_selected else enums.ButtonStyle.DEFAULT
            ),
        ],
        [
            InlineKeyboardButton(
                "✖️ Close",
                callback_data="close",
                style=enums.ButtonStyle.DANGER
            )
        ]
    ])


def settings_caption(play_mode: str) -> str:
    if play_mode == "admins":
        current = "🔒 **Admins Only**"
        explain = ">Only group admins can start, pause,\n>skip or stop playback."
    else:
        current = "🌍 **Everyone**"
        explain = ">Any member of this group can control\n>playback freely."

    return (
        "**◈ PLAY PERMISSION MODE ◈**\n\n"
        f"**Current:** {current}\n\n"
        f"{explain}\n\n"
        "<blockquote>🔒 **Admins Only** — safer for big or public groups.\n"
        "🌍 **Everyone** — best for friends and small chats.</blockquote>\n\n"
        "__Tap a button below to switch modes__"
    )


@Bot.on_message(filters.command(["set", "settings"]) & filters.group)
async def settings_panel(client: Bot, message: Message):
    chat_id = message.chat.id

    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
        await message.reply("🔒 **Only admins can open settings.**")
        return

    sm = SettingsManager(client.db)
    mode = await sm.get_play_mode(chat_id)

    card = await get_card(client)
    caption = settings_caption(mode)
    markup = settings_markup(mode)

    if card:
        await message.reply_photo(photo=card, caption=caption, reply_markup=markup)
    else:
        await message.reply(caption, reply_markup=markup)


@Bot.on_callback_query(filters.regex(r"^set_mode_(admins|everyone)$"))
async def change_mode(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id

    member = await client.get_chat_member(chat_id, callback.from_user.id)
    if member.status not in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
        await callback.answer("🔒 Only admins can change settings.", show_alert=True)
        return

    mode = callback.data.replace("set_mode_", "")
    sm = SettingsManager(client.db)
    await sm.set(chat_id, "play_mode", mode)

    await callback.answer(
        "🔒 Admins Only enabled" if mode == "admins" else "🌍 Everyone can now control playback"
    )

    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=settings_caption(mode),
                reply_markup=settings_markup(mode)
            )
        else:
            await callback.message.edit_text(
                text=settings_caption(mode),
                reply_markup=settings_markup(mode)
            )
    except Exception:
        pass