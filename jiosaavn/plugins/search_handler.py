import html
import logging
import traceback

from api.jiosaavn import Jiosaavn
from jiosaavn.bot import Bot

from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

logger = logging.getLogger(__name__)


# =========================================================
# FILTERS
# =========================================================

# PRIVATE:
# User directly song/album/artist ka naam bhej sakta hai.
# Commands, links aur via_bot messages ignore honge.
private_search_filter = (
    filters.text
    & filters.incoming
    & filters.private
    & ~filters.regex(r"^http.*")
    & ~filters.via_bot
    & ~filters.command([
        "start",
        "settings",
        "help",
        "about"
    ])
)


# GROUP:
# Group/Supergroup me ONLY:
#
# /am song name
#
# par search chalega.
group_search_filter = (
    filters.command("am")
    & filters.incoming
    & filters.group
)


# =========================================================
# SEARCH HANDLER
# =========================================================

@Bot.on_callback_query(filters.regex(r"^search#"))
@Bot.on_message(private_search_filter | group_search_filter)
async def search(
    client: Bot,
    message: Message | CallbackQuery
):

    try:

        # =================================================
        # NORMAL MESSAGE
        # =================================================

        if isinstance(message, Message):

            send_msg = await message.reply(
                "__**Processing... ⏳**__",
                quote=True
            )

            # ---------------------------------------------
            # PRIVATE CHAT
            # ---------------------------------------------

            if message.chat.type == "private":

                query = message.text.strip()

            # ---------------------------------------------
            # GROUP / SUPERGROUP
            # /am Alan Walker Spectre
            # ---------------------------------------------

            else:

                if len(message.command) < 2:

                    return await send_msg.edit(
                        "❌ Please enter a song name.\n\n"
                        "**Example:**\n"
                        "`/am Alan Walker Spectre`"
                    )

                # Everything after /am becomes query
                query = " ".join(
                    message.command[1:]
                ).strip()

            # ---------------------------------------------
            # GET USER SETTINGS
            # ---------------------------------------------

            user_data = await client.db.get_user(
                message.from_user.id
            )

            if user_data:
                search_type = user_data.get(
                    "type",
                    "all"
                )
            else:
                search_type = "all"

            page_no = 1

        # =================================================
        # CALLBACK QUERY
        # =================================================

        else:

            await message.answer()

            send_msg = message.message

            data = message.data.split("#")

            search_type = (
                data[1]
                if len(data) > 1
                else "all"
            )

            page_no = 1

            if len(data) >= 3:

                try:
                    page_no = int(data[2])
                except (ValueError, TypeError):
                    page_no = 1

            # Original search message
            reply_message = (
                message.message.reply_to_message
            )

            if reply_message and reply_message.text:

                query = reply_message.text.strip()

                # If original query was:
                # /am Alan Walker
                # remove /am
                if query.startswith("/am"):

                    parts = query.split(
                        maxsplit=1
                    )

                    if len(parts) == 2:
                        query = parts[1].strip()

            else:

                return await send_msg.edit(
                    "❌ Could not find the original "
                    "search query."
                )


        # =================================================
        # EMPTY QUERY CHECK
        # =================================================

        if not query:

            return await send_msg.edit(
                "❌ Please enter a song name."
            )


        # =================================================
        # SEARCH JIOSAAVN
        # =================================================

        try:

            if search_type in (
                "all",
                "topquery"
            ):

                response = (
                    await Jiosaavn()
                    .search_all_types(
                        query=query
                    )
                )

            else:

                response = (
                    await Jiosaavn()
                    .search(
                        query=query,
                        search_type=search_type,
                        page_no=page_no
                    )
                )

        except RuntimeError as e:

            logger.error(
                "JioSaavn API error: %s",
                e
            )

            traceback.print_exc()

            return await send_msg.edit(
                "❌ Connection refused by "
                "JioSaavn API.\n\n"
                "Please try again."
            )

        except Exception as e:

            logger.exception(
                "Unexpected JioSaavn search error"
            )

            return await send_msg.edit(
                "❌ Search failed.\n\n"
                f"`{type(e).__name__}: {e}`"
            )


        # =================================================
        # NO RESPONSE
        # =================================================

        if not response:

            return await send_msg.edit(
                "🔎 No search result found for "
                f"your query `{query}`"
            )


        buttons = []


        # =================================================
        # ALL / TOP QUERY
        # =================================================

        if search_type in (
            "all",
            "topquery"
        ):

            button_song_type_map = {

                "songs": (
                    "🎙 Songs",
                    "search#songs"
                ),

                "albums": (
                    "📚 Albums",
                    "search#albums"
                ),

                "playlists": (
                    "💾 Playlists",
                    "search#playlists"
                ),

                "artists": (
                    "👨‍🎤 Artists",
                    "search#artists"
                ),

                "topquery": (
                    "✨ Top Result",
                    "search#topquery"
                ),
            }


            # =============================================
            # TOP QUERY
            # =============================================

            if search_type == "topquery":

                topquery_data = (
                    response
                    .get(
                        "topquery",
                        {}
                    )
                    .get(
                        "data",
                        []
                    )
                )

                sub_sorted_data = sorted(
                    topquery_data,
                    key=lambda x: x.get(
                        "position",
                        0
                    )
                )


                for item in sub_sorted_data:

                    title = html.unescape(
                        item.get(
                            "title",
                            "Unknown"
                        )
                    )

                    album = item.get(
                        "album"
                    )

                    item_type = item.get(
                        "type"
                    )

                    item_url = item.get(
                        "url",
                        "/"
                    )

                    item_id = item_url.rstrip(
                        "/"
                    ).rsplit(
                        "/",
                        1
                    )[-1]


                    type_emoji_map = {

                        "song": "🎙",

                        "album": "📚",

                        "playlist": "💾",

                        "artist": "👨‍🎤"
                    }


                    if (
                        item_type
                        not in type_emoji_map
                    ):
                        continue


                    emoji = (
                        type_emoji_map[
                            item_type
                        ]
                    )


                    if album:

                        button_text = (
                            f"{emoji} {title} "
                            f"from {album}"
                        )

                    else:

                        button_text = (
                            f"{emoji} {title}"
                        )


                    callback_data = (
                        f"{item_type}#"
                        f"{item_id}#"
                        "topquery"
                    )


                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=button_text,
                                callback_data=(
                                    callback_data
                                )
                            )
                        ]
                    )


            # =============================================
            # ALL SEARCH
            # =============================================

            else:

                sorted_data = sorted(
                    response.items(),
                    key=lambda value:
                    value[1].get(
                        "position",
                        0
                    )
                    if isinstance(
                        value[1],
                        dict
                    )
                    else 0
                )


                for (
                    result_type,
                    result
                ) in sorted_data:


                    if (
                        result_type
                        not in
                        button_song_type_map
                    ):
                        continue


                    if not isinstance(
                        result,
                        dict
                    ):
                        continue


                    if result.get("data"):

                        (
                            button_label,
                            callback_data
                        ) = (
                            button_song_type_map[
                                result_type
                            ]
                        )


                        buttons.append(
                            [
                                InlineKeyboardButton(
                                    text=button_label,
                                    callback_data=(
                                        callback_data
                                    )
                                )
                            ]
                        )


            text = (
                f"**🔍 Search Query:** "
                f"{query}\n\n"
                "__Please select one "
                "category 👇__"
            )


        # =================================================
        # SONG / ALBUM / PLAYLIST / ARTIST RESULTS
        # =================================================

        else:

            total_results = response.get(
                "total",
                0
            )


            for result in response.get(
                "results",
                []
            ):

                perma_url = result.get(
                    "perma_url",
                    "/"
                )


                item_id = (
                    perma_url
                    .rstrip("/")
                    .rsplit("/", 1)[-1]
                )


                title = html.unescape(
                    result.get(
                        "title",
                        "Unknown"
                    )
                )


                result_type = result.get(
                    "type",
                    "unknown"
                )


                artist = html.unescape(
                    result.get(
                        "name",
                        "Unknown"
                    )
                )


                more_info = result.get(
                    "more_info",
                    {}
                ) or {}


                album = more_info.get(
                    "album",
                    ""
                )


                button_label_map = {

                    "song": (
                        f"🎙 {title} "
                        f"from '{album}'"
                        if album
                        else f"🎙 {title}"
                    ),

                    "album": (
                        f"📚 {title}"
                    ),

                    "playlist": (
                        f"💾 {title}"
                    ),

                    "artist": (
                        f"👨‍🎤 {artist}"
                    )
                }


                button_label = (
                    button_label_map.get(
                        result_type
                    )
                )


                if button_label:

                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=button_label,
                                callback_data=(
                                    f"{result_type}"
                                    f"#{item_id}"
                                )
                            )
                        ]
                    )


            # =============================================
            # PAGE NAVIGATION
            # =============================================

            text = (
                f"**📈 Total Results:** "
                f"{total_results}\n\n"
                f"**🔍 Search Query:** "
                f"{query}\n\n"
                f"**📜 Page No:** "
                f"{page_no}"
            )


            navigation_buttons = []


            if page_no > 1:

                navigation_buttons.append(
                    InlineKeyboardButton(
                        "⬅️",
                        callback_data=(
                            f"search#"
                            f"{search_type}#"
                            f"{page_no - 1}"
                        )
                    )
                )


            if total_results > (
                10 * page_no
            ):

                navigation_buttons.append(
                    InlineKeyboardButton(
                        "➡️",
                        callback_data=(
                            f"search#"
                            f"{search_type}#"
                            f"{page_no + 1}"
                        )
                    )
                )


            if navigation_buttons:

                buttons.append(
                    navigation_buttons
                )


        # =================================================
        # NO BUTTONS
        # =================================================

        if not buttons:

            return await send_msg.edit(
                "🔎 No search result found for "
                f"your query `{query}`"
            )


        # =================================================
        # CLOSE BUTTON
        # =================================================

        buttons.append(
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        )


        # =================================================
        # SEND RESULTS
        # =================================================

        await send_msg.edit(
            text,
            reply_markup=InlineKeyboardMarkup(
                buttons
            )
        )


    # =====================================================
    # FINAL ERROR HANDLER
    # =====================================================

    except Exception as e:

        logger.exception(
            "Error inside search handler"
        )

        traceback.print_exc()

        try:

            if "send_msg" in locals():

                await send_msg.edit(
                    "❌ Something went wrong.\n\n"
                    f"`{type(e).__name__}: {e}`"
                )

        except Exception:
            pass