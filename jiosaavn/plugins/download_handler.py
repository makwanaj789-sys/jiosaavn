import os
import html
import time
import shutil
import logging
from datetime import datetime

from jiosaavn.bot import Bot
from api.download_engine import DownloadEngine
from api.search_engine import SearchEngine

import aiohttp
import aiofiles

from pyrogram import filters
from mutagen.mp4 import MP4, MP4Cover

from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from pyrogram.enums import ChatAction


logger = logging.getLogger(__name__)


# =========================================================
# OWNER BUTTON
# =========================================================

OWNER_URL = "https://t.me/umclon"


def get_owner_button():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👑 —͟͞͞𝗔ᴊ፝֟፝֟ᴀʏ 〆 ⚡",
                    url=OWNER_URL
                )
            ]
        ]
    )


# =========================================================
# DATE FORMATTER
# 2024-06-09 -> 09 Jun 2024
# =========================================================

def format_release_date(date_value, year_value=None):

    if date_value:
        try:
            parsed = datetime.strptime(
                str(date_value),
                "%Y-%m-%d"
            )

            return parsed.strftime(
                "%d %b %Y"
            )

        except (ValueError, TypeError):
            return str(date_value)

    if year_value:
        return str(year_value)

    return "Unknown"


# =========================================================
# DOWNLOAD HANDLER
# =========================================================

@Bot.on_callback_query(filters.regex(r"^upload#"))
@Bot.on_message(
    filters.regex(r"http.*")
    & filters.private
    & filters.incoming
)
async def download(
    client: Bot,
    message: Message | CallbackQuery
):

    # =====================================================
    # CALLBACK QUERY
    # =====================================================

    if isinstance(message, CallbackQuery):

        _, item_id, search_type = message.data.split("#")

        msg = await message.message.edit(
            "**⚡ Processing your request...**"
        )

    # =====================================================
    # DIRECT JIOSAAVN LINK
    # =====================================================

    else:

        msg = await message.reply(
            "**⚡ Processing your request...**",
            quote=True
        )

        query = message.text

        item_id = query.rsplit(
            "/",
            1
        )[1]

        if "song" in query:
            search_type = "song"

        elif "album" in query:
            search_type = "album"

        elif "featured" in query:
            search_type = "playlist"

        elif "artist" in query:
            search_type = "artist"

        else:
            return await msg.edit(
                "❌ **Unsupported JioSaavn URL.**"
            )

    # =====================================================
    # SONG
    # =====================================================

    if search_type == "song":

        await download_tool(
            client,
            message,
            msg,
            item_id
        )

    # =====================================================
    # ALBUM / PLAYLIST
    # =====================================================

    elif search_type in (
        "album",
        "playlist"
    ):

        page_no = 1

        album_id = (
            item_id
            if search_type == "album"
            else None
        )

        playlist_id = (
            item_id
            if search_type == "playlist"
            else None
        )

        while True:

            response = (
                await SearchEngine()
                .get_playlist_or_album(
                    album_id=album_id,
                    playlist_id=playlist_id,
                    page_no=page_no
                )
            )

            if (
                not response
                or not response.get("list")
            ):
                break

            songs = response["list"]

            for song in songs:

                song_url = song.get(
                    "perma_url",
                    ""
                )

                if not song_url:
                    continue

                song_id = song_url.rsplit(
                    "/",
                    1
                )[-1]

                await download_tool(
                    client,
                    message,
                    msg,
                    song_id
                )

            page_no += 1

    # =====================================================
    # UNSUPPORTED
    # =====================================================

    else:

        await msg.edit(
            "❌ **Artists and Podcast upload "
            "not supported.**"
        )

        return

    # =====================================================
    # DELETE PROCESSING MESSAGE
    # =====================================================

    try:

        if msg.text and "Failed" not in msg.text:
            await msg.delete()

    except Exception:
        pass


# =========================================================
# DOWNLOAD TOOL
# =========================================================

async def download_tool(
    client: Bot,
    message: Message | CallbackQuery,
    msg: Message,
    song_id: str
):

    # =====================================================
    # DESTINATION CHAT
    # =====================================================

    if isinstance(message, CallbackQuery):
        target_chat_id = message.message.chat.id
    else:
        target_chat_id = message.chat.id

    # =====================================================
    # REQUESTER
    #
    # CallbackQuery -> person who clicked final button
    # Direct URL    -> person who sent URL
    # =====================================================

    requester = message.from_user

    user_id = requester.id

    requester_name = (
        requester.first_name
        or requester.username
        or "Music Lover"
    )

    # Escape Telegram Markdown special characters in name
    requester_name = (
        str(requester_name)
        .replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )

    # tg://user?id works even when user has no public username
    requester_link = (
        f"tg://user?id={user_id}"
    )

    reply_message_id = msg.id

    # =====================================================
    # USER SETTINGS
    # =====================================================

    user = await client.db.get_user(
        user_id
    )

    if user:
        quality = user.get(
            "quality",
            "320kbps"
        )
    else:
        quality = "320kbps"

    bitrate = (
        320
        if quality == "320kbps"
        else 160
    )

    # =====================================================
    # CACHE INFO
    #
    # Don't return immediately here because we first need
    # fresh metadata + requester caption.
    # =====================================================

    is_exist = await client.db.is_song_id_exist(
        song_id
    )

    cached_song = None

    if is_exist:

        try:

            cached_data = await client.db.get_song(
                song_id
            )

            if cached_data:
                cached_song = cached_data.get(
                    quality
                )

        except Exception as e:

            logger.warning(
                "Cache lookup failed: %s",
                e
            )

    # =====================================================
    # GET SONG DATA
    # =====================================================

    song_response = await SearchEngine().get_song(
        song_id=song_id
    )

    if (
        not song_response
        or not song_response.get("songs")
    ):

        return await msg.edit(
            "❌ **Song information could not be fetched.**"
        )

    song_data = song_response["songs"][0]

    # =====================================================
    # METADATA
    # =====================================================

    title = html.unescape(
        str(
            song_data.get(
                "title",
                "Unknown"
            )
        )
    )

    formatted_title = title.replace(
        " ",
        "-"
    )

    language = song_data.get(
        "language",
        "Unknown"
    )

    more_info = song_data.get(
        "more_info",
        {}
    ) or {}

    album = html.unescape(
        str(
            more_info.get(
                "album",
                "Unknown"
            )
        )
    )

    artist_map = more_info.get(
        "artistMap",
        {}
    ) or {}

    artists = artist_map.get(
        "artists",
        []
    ) or []

    # =====================================================
    # ARTIST HELPER
    # =====================================================

    def get_artist_by_role(
        role: str
    ) -> str:

        return ", ".join(
            artist.get("name")
            for artist in artists
            if (
                artist.get("role") == role
                and artist.get("name")
            )
        )

    music = (
        more_info.get("music")
        or get_artist_by_role("music")
    )

    singers = (
        get_artist_by_role("singer")
        or music
        or "Unknown"
    )

    singers = html.unescape(
        str(singers)
    )

    release_date = more_info.get(
        "release_date"
    )

    release_year = song_data.get(
        "year"
    )

    pretty_date = format_release_date(
        release_date,
        release_year
    )

    copyright_text = more_info.get(
        "copyright_text",
        "Unknown"
    )

    try:

        duration = int(
            more_info.get(
                "duration",
                "0"
            ) or 0
        )

    except (ValueError, TypeError):
        duration = 0

    album_url = more_info.get(
        "album_url",
        ""
    )

    image_url = (
        song_data.get(
            "image",
            ""
        )
        .replace(
            "150x150",
            "500x500"
        )
    )

    song_url = song_data.get(
        "perma_url",
        (
            "https://jiosaavn.com/"
            f"songs/{formatted_title}/{song_id}"
        )
    )

    # =====================================================
    # NEW UNIQUE CAPTION
    # =====================================================

    text_data = []

    # Song + clickable JioSaavn URL
    text_data.append(
        f"🎧  **[{title}]({song_url})**"
    )

    # Artist
    text_data.append(
        f"     └─ {singers}"
    )

    text_data.append("")

    # Album
    if album:

        if album_url:
            text_data.append(
                f"💿  **[{album}]({album_url})**"
            )
        else:
            text_data.append(
                f"💿  **{album}**"
            )

    # Language + quality
    text_data.append(
        f"🌐  {str(language).title()}  ·  "
        f"**{quality}**"
    )

    # Date
    text_data.append(
        f"📆  {pretty_date}"
    )

    text_data.append("")
    text_data.append(
        "      ── ♪ ♫ ♪ ──"
    )
    text_data.append("")

    # =====================================================
    # CLICKABLE REQUESTER
    # =====================================================

    text_data.append(
        "🪽  **𝗧𝗵𝗶𝘀 𝘁𝗿𝗮𝗰𝗸 𝘄𝗮𝘀 "
        "𝗽𝗶𝗰𝗸𝗲𝗱 𝗯𝘆**"
    )

    text_data.append(
        f"     ✦ [{requester_name}]"
        f"({requester_link}) ✦"
    )

    text_data.append("")

    text_data.append(
        "♡  **listen • feel • repeat**"
    )

    caption = "\n".join(
        text_data
    )

    # =====================================================
    # DOWNLOAD DIRECTORY
    # =====================================================

    download_dir = (
        f"./download/"
        f"{time.time()}_{user_id}/"
    )

    os.makedirs(
        download_dir,
        exist_ok=True
    )

    # =====================================================
    # SAFE FILE NAME
    # =====================================================

    safe_title = "".join(
        c
        for c in title
        if c not in '\\/:*?"<>|'
    )

    pre_file_name = (
        f"{download_dir}"
        f"{safe_title}_{quality}.mp4"
    )

    file_name = (
        f"{download_dir}"
        f"{safe_title}_{quality}.mp3"
    )

    thumbnail_location = (
        f"{download_dir}"
        f"{safe_title}.jpg"
    )

    try:

        # =================================================
        # IF SONG IS CACHED
        #
        # We copy the audio but replace old caption with
        # fresh caption containing CURRENT requester.
        # =================================================

        if cached_song:

            try:

                song_msg = await client.get_messages(
                    chat_id=int(
                        cached_song.get("chat_id")
                    ),
                    message_ids=int(
                        cached_song.get("message_id")
                    )
                )

                if not song_msg.empty:

                    is_sent = await song_msg.copy(
                        chat_id=target_chat_id,
                        reply_to_message_id=reply_message_id,
                        caption=caption,
                        reply_markup=get_owner_button()
                    )

                    if is_sent:
                        return

            except Exception as e:

                logger.warning(
                    "Cached song copy failed: %s",
                    e
                )

        # =================================================
        # DOWNLOADING STATUS
        # =================================================

        await msg.edit(
            f"📥 **Downloading...**\n\n"
            f"🎵 `{title}`"
        )

        await client.send_chat_action(
            chat_id=target_chat_id,
            action=ChatAction.RECORD_AUDIO
        )

        # =================================================
        # DOWNLOAD JIOSAAVN THUMBNAIL
        # =================================================

        headers = {

            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/117.0.0.0 "
                "Safari/537.36"
            ),

            "Referer": (
                "https://www.jiosaavn.com/"
            )
        }

        cover_art = None

        if image_url:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    image_url,
                    headers=headers
                ) as response:

                    if response.status == 200:

                        cover_art = (
                            await response.read()
                        )

                        async with aiofiles.open(
                            thumbnail_location,
                            "wb"
                        ) as file:

                            await file.write(
                                cover_art
                            )

        # =================================================
        # DOWNLOAD AUDIO
        # =================================================

        pre_audio = (
            await DownloadEngine()
            .download(
                song_id=song_id,
                bitrate=bitrate,
                download_location=pre_file_name
            )
        )

        # =================================================
        # ADD METADATA
        # =================================================

        audio = MP4(
            pre_audio
        )

        audio["\xa9nam"] = title
        audio["\xa9alb"] = album
        audio["\xa9ART"] = singers

        audio["\xa9cmt"] = (
            f"Aarti Music - {song_url}"
        )

        audio["cprt"] = copyright_text

        if release_year:

            audio["\xa9day"] = str(
                release_year
            )

        if cover_art:

            audio["covr"] = [
                MP4Cover(
                    cover_art,
                    imageformat=(
                        MP4Cover.FORMAT_JPEG
                    )
                )
            ]

        audio.save()

        os.rename(
            pre_audio,
            file_name
        )

        # =================================================
        # UPLOAD STATUS
        # =================================================

        await msg.edit(
            f"📤 **Uploading...**\n\n"
            f"🎧 `{title}`"
        )

        await client.send_chat_action(
            chat_id=target_chat_id,
            action=ChatAction.UPLOAD_AUDIO
        )

        # =================================================
        # SEND AUDIO
        # =================================================

        send_audio_kwargs = {

            "chat_id": target_chat_id,

            "audio": file_name,

            "caption": caption,

            "duration": duration,

            "title": title,

            "performer": singers,

            "reply_to_message_id": reply_message_id,

            "reply_markup": get_owner_button()
        }

        # =================================================
        # JIOSAAVN THUMBNAIL
        # =================================================

        if os.path.exists(
            thumbnail_location
        ):

            send_audio_kwargs[
                "thumb"
            ] = thumbnail_location

        # =================================================
        # SEND
        # =================================================

        song_file = await client.send_audio(
            **send_audio_kwargs
        )

        # =================================================
        # UPLOAD FAILED
        # =================================================

        if not song_file:

            return await msg.edit(
                "❌ **Failed to upload song.**"
            )

        # =================================================
        # SAVE CACHE
        # =================================================

        await client.db.update_song(
            song_id,
            quality,
            song_file.chat.id,
            song_file.id
        )

    except Exception as e:

        logger.exception(
            "Download/upload failed"
        )

        try:

            await msg.edit(
                "❌ **Song download/upload failed.**\n\n"
                f"`{type(e).__name__}: {e}`"
            )

        except Exception:
            pass

    finally:

        # =================================================
        # CLEAN TEMP FILES
        # =================================================

        if os.path.isdir(
            download_dir
        ):

            try:

                shutil.rmtree(
                    download_dir
                )

            except Exception:

                logger.exception(
                    "Could not remove download directory"
                )