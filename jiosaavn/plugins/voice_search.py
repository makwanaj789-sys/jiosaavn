import os
import logging
import tempfile

from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from jiosaavn.bot import Bot
from jiosaavn.emojis import *
from api.transcribe import transcribe
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

# Telegram voice notes are small, but guard against odd uploads
MAX_DURATION = 60      # seconds
MAX_RESULTS = 8


async def handle_voice(client: Bot, message: Message, quoted: Message):
    """
    Downloads a voice note, transcribes it, and shows search results.
    `quoted` is the message carrying the audio (may be the same message).
    """
    voice = quoted.voice or quoted.audio

    if not voice:
        await message.reply(
            f"**◈ ɴᴏ ᴠᴏɪᴄᴇ ꜰᴏᴜɴᴅ ◈**\n\n"
            f">{E_WRITE} Reply to a voice note with `/vs`"
        )
        return

    if getattr(voice, "duration", 0) > MAX_DURATION:
        await message.reply(
            f"**◈ ᴛᴏᴏ ʟᴏɴɢ ◈**\n\n"
            f">{E_STOP} Keep it under `{MAX_DURATION}` seconds.\n"
            f">Just say the song name."
        )
        return

    status = await message.reply(E_SEARCH)
    filepath = None

    try:
        filepath = await client.download_media(
            quoted,
            file_name=os.path.join(tempfile.gettempdir(), f"vs_{quoted.id}.ogg")
        )

        text = await transcribe(filepath)

        if not text:
            await status.edit_text(
                f"**◈ ᴄᴏᴜʟᴅɴ'ᴛ ʜᴇᴀʀ ᴛʜᴀᴛ ◈**\n\n"
                f">{E_STOP} Try again in a quieter spot,\n"
                f">and say just the song name."
            )
            return

        await status.edit_text(f"{E_SEARCH} **{text}**")

        # Track it like any other search
        try:
            await client.db.add_search(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                query=text
            )
        except Exception:
            pass

        engine = SearchEngine()
        response = await engine.search(text)
        results = (response.get("results") or [])[:MAX_RESULTS]

        if not results:
            await status.edit_text(
                f"**◈ ɴᴏ ʀᴇꜱᴜʟᴛꜱ ◈**\n\n"
                f">{E_SPEAK} I heard **{text}**\n"
                f">{E_STOP} but found nothing for it."
            )
            return

        buttons = []
        for r in results:
            vid = r.get("id")
            if not vid:
                continue

            title = r.get("title", "Unknown")
            artist = r.get("uploader", "Unknown")
            duration = r.get("duration", 0)
            dur = f"{duration//60}:{duration%60:02d}" if duration else "N/A"

            buttons.append([
                InlineKeyboardButton(
                    f"{title} — {artist} ({dur})"[:60],
                    callback_data=f"youtube#{vid}",
                    style=enums.ButtonStyle.PRIMARY,
                    icon_custom_emoji_id="5911274703367968100"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "ᴄʟᴏꜱᴇ",
                callback_data="close",
                style=enums.ButtonStyle.DANGER,
                icon_custom_emoji_id="5974083768233760323"
            )
        ])

        await status.edit_text(
            f"**◈ ʜᴇᴀʀᴅ ʏᴏᴜ ◈**\n\n"
            f">{E_SPEAK} **{text}**\n"
            f">{E_CASSETTE} Found `{len(buttons) - 1}` tracks\n\n"
            f"__{E_SPARKLE} Tap any track to download__",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"voice_search error: {e}")
        await status.edit_text(f"**◈ ᴇʀʀᴏʀ ◈**\n\n>`{e}`")

    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass


@Bot.on_message(filters.voice & filters.private)
async def voice_dm(client: Bot, message: Message):
    """In DMs, just send a voice note — no command needed."""
    await handle_voice(client, message, message)


@Bot.on_message(filters.command(["vs", "voicesearch"]))
async def voice_command(client: Bot, message: Message):
    """In groups, reply to a voice note with /vs."""
    quoted = message.reply_to_message

    if not quoted:
        await message.reply(
            f"**◈ ᴠᴏɪᴄᴇ ꜱᴇᴀʀᴄʜ ◈**\n\n"
            f">{E_SPEAK} Reply to a voice note with `/vs`\n"
            f">and I'll find the song you named.\n\n"
            f"__{E_SPARKLE} In DMs you can just send the voice note__"
        )
        return

    await handle_voice(client, message, quoted)