import os
import html
import time
import shutil
import logging

from jiosaavn.bot import Bot
from api.jiosaavn import Jiosaavn

import aiohttp
import aiofiles

from pyrogram import filters
from mutagen.mp4 import MP4, MP4Cover

from pyrogram.types import (
    Message,
    CallbackQuery
)

from pyrogram.enums import ChatAction


logger = logging.getLogger(__name__)


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
            "**Processing...**"
        )

    # =====================================================
    # DIRECT JIOSAAVN LINK IN PRIVATE
    # =====================================================

    else:

        msg = await message.reply(
            "**Processing...**",
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
                "❌ Unsupported JioSaavn URL."
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
                await Jiosaavn()
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
            "Artists and Podcast upload "
            "not supported."
        )

        return


    # Delete processing message
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
    # IMPORTANT:
    # Determine destination chat
    #
    # Private -> private chat
    # Group   -> same group
    # =====================================================

    if isinstance(message, CallbackQuery):

        target_chat_id = message.message.chat.id

    else:

        target_chat_id = message.chat.id


    user_id = message.from_user.id


    # =====================================================
    # REPLY MESSAGE
    # =====================================================

    # We reply to the processing/search message when possible.
    # This avoids using a private user's message ID inside GC.

    reply_message_id = msg.id


    # =====================================================
    # USER SETTINGS
    # =====================================================

    is_exist = await client.db.is_song_id_exist(
        song_id
    )


    user = await client.db.get_user(
        user_id
    )


    # Default quality if DB data isn't available
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
    # CHECK CACHED SONG
    # =====================================================

    if is_exist:

        cached_data = await client.db.get_song(
            song_id
        )


        if cached_data:

            song = cached_data.get(
                quality
            )

        else:

            song = None


        if song:

            try:

                song_msg = await client.get_messages(
                    chat_id=int(
                        song.get("chat_id")
                    ),
                    message_ids=int(
                        song.get("message_id")
                    )
                )


                if not song_msg.empty:

                    # IMPORTANT:
                    # Copy to SAME chat where request came from
                    is_sent = await song_msg.copy(
                        chat_id=target_chat_id,
                        reply_to_message_id=reply_message_id
                    )


                    if is_sent:
                        return

            except Exception as e:

                logger.warning(
                    "Cached song copy failed: %s",
                    e
                )


    # =====================================================
    # GET SONG DATA
    # =====================================================

    song_response = await Jiosaavn().get_song(
        song_id=song_id
    )


    if (
        not song_response
        or not song_response.get("songs")
    ):

        return await msg.edit(
            "❌ Song information could not be fetched."
        )


    song_data = song_response["songs"][0]


    # =====================================================
    # METADATA
    # =====================================================

    title = song_data.get(
        "title",
        "Unknown"
    )

    title = html.unescape(
        title
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


    album = more_info.get(
        "album",
        "Unknown"
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


    release_date = more_info.get(
        "release_date"
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


    release_year = song_data.get(
        "year"
    )


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
    # CAPTION
    # =====================================================

    text_data = []


    if image_url:

        text_data.append(
            f"[\u2063]({image_url})"
            f"**🎧 Song:** "
            f"[{title}]({song_url})"
        )

    elif title:

        text_data.append(
            f"**🎧 Song:** "
            f"[{title}]({song_url})"
        )


    if album:

        if album_url:

            text_data.append(
                f"**📚 Album:** "
                f"[{album}]({album_url})"
            )

        else:

            text_data.append(
                f"**📚 Album:** {album}"
            )


    if language:

        text_data.append(
            f"**📰 Language:** "
            f"{language}"
        )


    if release_date:

        text_data.append(
            f"**📆 Release Date:** "
            f"__{release_date}__"
        )


    elif release_year:

        text_data.append(
            f"**📆 Release Year:** "
            f"__{release_year}__"
        )


    caption = "\n\n".join(
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


    # Make filename safer
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
        # DOWNLOADING STATUS
        # =================================================

        await msg.edit(
            f"__📥 Downloading {title}__"
        )


        # IMPORTANT:
        # Show action in originating chat
        await client.send_chat_action(
            chat_id=target_chat_id,
            action=ChatAction.RECORD_AUDIO
        )


        # =================================================
        # DOWNLOAD THUMBNAIL
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
            await Jiosaavn()
            .download_song(
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
            f"Powered by AartiMusic - "
            f"{song_url}"
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
            f"__📤 Uploading {title}__"
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
            "reply_to_message_id": reply_message_id
        }


        # Only use thumb if successfully downloaded
        if os.path.exists(
            thumbnail_location
        ):

            send_audio_kwargs[
                "thumb"
            ] = thumbnail_location


        song_file = await client.send_audio(
            **send_audio_kwargs
        )


        # =================================================
        # UPLOAD FAILED
        # =================================================

        if not song_file:

            return await msg.edit(
                "❌ Failed to upload song."
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
                "❌ Song download/upload failed.\n\n"
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