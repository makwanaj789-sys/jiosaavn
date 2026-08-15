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
from jiosaavn.emojis import *
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
                f"{'✦ ' if admins_selected else ''}ᴀᴅᴍɪɴꜱ ᴏɴʟʏ",
                callback_data="set_mode_admins",
                style=enums.ButtonStyle.SUCCESS if admins_selected else enums.ButtonStyle.DEFAULT
            ),
            InlineKeyboardButton(
                f"{'✦ ' if not admins_selected else ''}ᴇᴠᴇʀʏᴏɴᴇ",
                callback_data="set_mode_everyone",
                style=enums.ButtonStyle.SUCCESS if not admins_selected else enums.ButtonStyle.DEFAULT
            ),
        ],
        [
            InlineKeyboardButton(
                "ᴀᴅᴅ ᴍᴇ",
                url="https://t.me/AartiMusic_bot?startgroup=true",
                style=enums.ButtonStyle.PRIMARY
            ),
            InlineKeyboardButton(
                "ᴄʟᴏꜱᴇ",
                callback_data="close",
                style=enums.ButtonStyle.DANGER
            )
        ]
    ])


def settings_caption(play_mode: str) -> str:
    if play_mode == "admins":
        current = f"{E_SHIELD} **ᴀᴅᴍɪɴꜱ ᴏɴʟʏ**"
        explain = ">Only group admins can start, pause,\n>skip or stop playback."
    else:
        current = f"{E_SPEAK} **ᴇᴠᴇʀʏᴏɴᴇ**"
        explain = ">Any member of this group can control\n>playback freely."

    return (
        f"**◈ ᴘʟᴀʏ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴍᴏᴅᴇ ◈**\n\n"
        f"**ᴄᴜʀʀᴇɴᴛ:** {current}\n\n"
        f"{explain}\n\n"
        f"<blockquote>{E_SHIELD} **ᴀᴅᴍɪɴꜱ ᴏɴʟʏ** — safer for big or public groups.\n"
        f"{E_SPEAK} **ᴇᴠᴇʀʏᴏɴᴇ** — best for friends and small chats.</blockquote>\n\n"
        f"__{E_SETTINGS} Tap a button below to switch modes__"
    )


@Bot.on_message(filters.command(["set", "settings"]) & filters.group)
async def settings_panel(client: Bot, message: Message):
    chat_id = message.chat.id

    member = await client.get_chat_member(chat_id, message.from_user.id)
    if member.status not in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
        await message.reply(f"{E_SHIELD} **ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴏᴘᴇɴ ꜱᴇᴛᴛɪɴɢꜱ**")
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
        await callback.answer("🔒 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴄʜᴀɴɢᴇ ꜱᴇᴛᴛɪɴɢꜱ", show_alert=True)
        return

    mode = callback.data.replace("set_mode_", "")
    sm = SettingsManager(client.db)
    await sm.set(chat_id, "play_mode", mode)

    await callback.answer(
        "🛡 ᴀᴅᴍɪɴꜱ ᴏɴʟʏ ᴇɴᴀʙʟᴇᴅ" if mode == "admins"
        else "🗣 ᴇᴠᴇʀʏᴏɴᴇ ᴄᴀɴ ɴᴏᴡ ᴄᴏɴᴛʀᴏʟ ᴘʟᴀʏʙᴀᴄᴋ"
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