import logging
import traceback

from pyrogram import enums
from pyrogram.types import (
    ChosenInlineResult,
    InputMediaAudio,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from jiosaavn.bot import Bot
from jiosaavn.emojis import *
from api.inline_helper import InlineHelper

logger = logging.getLogger(__name__)


@Bot.on_chosen_inline_result()
async def on_chosen(client, result: ChosenInlineResult):
    result_id = result.result_id
    logger.info(f"🎯 CHOSEN INLINE RESULT: {result_id}")

    if not result_id.startswith("dl_"):
        return

    video_id = result_id.replace("dl_", "")
    inline_message_id = result.inline_message_id
    logger.info(f"📩 inline_message_id: {inline_message_id}")

    if not inline_message_id:
        logger.warning("❌ No inline_message_id received — cannot edit message.")
        return

    try:
        helper = InlineHelper(client)
        song = await helper.get_or_create(video_id)

        if not song:
            await client.edit_inline_text(
                inline_message_id,
                f"**◈ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ ◈**\n\n>{E_STOP} Couldn't fetch that track."
            )
            return

        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "ᴀᴅᴅ ᴛᴏ ꜰᴀᴠᴏʀɪᴛᴇꜱ",
                    callback_data=f"fav_add_{video_id}",
                    style=enums.ButtonStyle.DANGER,
                    icon_custom_emoji_id="5255861796350224063"
                )
            ],
            [
                InlineKeyboardButton(
                    "ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                    url="https://t.me/AartiMusic_bot?startgroup=true",
                    style=enums.ButtonStyle.SUCCESS,
                    icon_custom_emoji_id="5861735798956627072"
                )
            ]
        ])

        await client.edit_inline_media(
            inline_message_id,
            InputMediaAudio(
                media=song["file_id"],
                caption=f"{E_TRACK} **{song['title']}**\n\n__{E_SPARKLE} ᴠɪᴀ ᴀᴀʀᴛɪᴍᴜꜱɪᴄ__"
            ),
            reply_markup=markup
        )

        logger.info(f"✅ INLINE MESSAGE EDITED SUCCESSFULLY: {song['title']}")

    except Exception as e:
        logger.error(f"❌ CHOSEN_INLINE_RESULT ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await client.edit_inline_text(
                inline_message_id,
                f"**◈ ᴇʀʀᴏʀ ◈**\n\n>`{type(e).__name__}: {e}`"
            )
        except Exception as e2:
            logger.error(f"❌ Even edit_text failed: {e2}")