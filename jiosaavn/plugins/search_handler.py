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
# SEARCH HANDLER
#
# PRIVATE:
#   Direct song/search query
#   Example: Tum Hi Ho
#
# GROUP:
#   Only /am command
#   Example: /am Tum Hi Ho
# =========================================================


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
        "about",
        "am"
    ])
)


group_search_filter = (
    filters.command("am")
    & filters.incoming
    & (filters.group | filters.supergroup)
)


@Bot.on_callback_query(filters.regex(r"^search#"))
@Bot.on_message(private_search_filter | group_search_filter)
async def search(
    client: Bot,
    message: Message | CallbackQuery
):

    # ==========================================
    # PREPARE QUERY
    # ==========================================

    if isinstance(message, Message):

        # Group / Supergroup
        if message.chat.type in ("group", "supergroup"):

            # /am without song name
            if len(message.command) < 2:
                return await message.reply(
                    "🎵 **Please enter a song name.**\n\n"
                    "**Example:** `/am Tum Hi Ho`",
                    quote=True
                )

            # Everything after /am becomes query
            query = " ".join(message.command[1:]).strip()

        # Private chat
        else:
            query = message.text.strip()

        send_msg = await message.reply(
            "__**Processing... ⏳**__",
            quote=True
        )

    # Callback query
    else:

        await message.answer()

        send_msg = message.message

        # Original search query
        if (
            message.message
            and message.message.reply_to_message
            and message.message.reply_to_message.text
        ):
            original_text = (
                message.message.reply_to_message.text.strip()
            )

            # If original message was /am query
            if original_text.startswith("/am "):
                query = original_text.split(
                    maxsplit=1
                )[1].strip()
            else:
                query = original_text

        else:
            return await message.answer(
                "Search query not found.",
                show_alert=True
            )

    # ==========================================
    # USER SETTINGS
    # ==========================================

    page_no = 1

    if isinstance(message, Message):

        user_data = await client.db.get_user(
            message.from_user.id
        )

        search_type = user_data["type"]

    else:

        data = message.data.split("#")

        search_type = data[1]

        if len(data) == 3:
            page_no = int(data[2])

    # ==========================================
    # JIOSAAVN SEARCH
    # ==========================================

    try:

        if search_type in ("all", "topquery"):

            response = await Jiosaavn().search_all_types(
                query=query
            )

        else:

            response = await Jiosaavn().search(
                query=query,
                search_type=search_type,
                page_no=page_no
            )

    except RuntimeError as e:

        logger.error(e)
        traceback.print_exc()

        return await send_msg.edit(
            "Connection refused by JioSaavn API. "
            "Please try again."
        )

    # ==========================================
    # NO RESULTS
    # ==========================================

    if not response:

        return await send_msg.edit(
            f"🔎 No search result found for "
            f"your query `{query}`"
        )

    buttons = []

    # ==========================================
    # ALL / TOP QUERY
    # ==========================================

    if search_type in ("all", "topquery"):

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

        # ======================================
        # TOP QUERY RESULTS
        # ======================================

        if search_type == "topquery":

            sub_sorted_data = sorted(
                response.get(
                    "topquery",
                    {}
                ).get(
                    "data",
                    []
                ),
                key=lambda x: x.get(
                    "position",
                    0
                )
            )

            for data in sub_sorted_data:

                title = data.get(
                    "title",
                    "unknown"
                )

                title = html.unescape(title)

                album = data.get("album")

                item_type = data.get("type")

                item_id = data.get(
                    "url",
                    "/"
                ).rsplit(
                    "/",
                    1
                )[1]

                type_emoji_map = {
                    "song": "🎙",
                    "album": "📚",
                    "playlist": "💾",
                    "artist": "👨‍🎤",
                }

                if item_type not in type_emoji_map:
                    continue

                emoji = type_emoji_map[
                    item_type
                ]

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
                    f"{item_id}#topquery"
                )

                buttons.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=callback_data
                    )
                ])

        # ======================================
        # CATEGORY SELECTION
        # ======================================

        else:

            sorted_data = sorted(
                response.items(),
                key=lambda value:
                value[1].get(
                    "position",
                    0
                )
            )

            for result_type, result in sorted_data:

                if (
                    result_type
                    not in button_song_type_map
                ):
                    continue

                if result.get("data"):

                    button_label, callback_data = (
                        button_song_type_map[
                            result_type
                        ]
                    )

                    buttons.append([
                        InlineKeyboardButton(
                            text=button_label,
                            callback_data=callback_data
                        )
                    ])

        text = (
            f"**🔍 Search Query:** {query}\n\n"
            "__Please select one category 👇__"
        )

    # ==========================================
    # SONG / ALBUM / PLAYLIST / ARTIST RESULTS
    # ==========================================

    else:

        total_results = response.get(
            "total",
            0
        )

        for result in response.get(
            "results",
            []
        ):

            item_id = result.get(
                "perma_url",
                "/"
            ).rsplit(
                "/",
                1
            )[1]

            title = result.get(
                "title",
                "unknown"
            )

            title = html.unescape(title)

            result_type = result.get(
                "type",
                "unknown"
            )

            artist = result.get(
                "name",
                "unknown"
            )

            artist = html.unescape(artist)

            more_info = result.get(
                "more_info",
                {}
            )

            album = more_info.get(
                "album",
                ""
            )

            button_label_map = {

                "song": (
                    f"🎙 {title} from '{album}'"
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
                ),
            }

            button_label = (
                button_label_map.get(
                    result_type
                )
            )

            if button_label:

                buttons.append([
                    InlineKeyboardButton(
                        text=button_label,
                        callback_data=(
                            f"{result_type}#"
                            f"{item_id}"
                        )
                    )
                ])

        text = (
            f"**📈 Total Results:** "
            f"{total_results}\n\n"
            f"**🔍 Search Query:** "
            f"{query}\n\n"
            f"**📜 Page No:** "
            f"{page_no}"
        )

        # ======================================
        # PAGINATION
        # ======================================

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

        if total_results > 10 * page_no:

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

    # ==========================================
    # FINAL RESPONSE
    # ==========================================

    if not buttons:

        return await send_msg.edit(
            f"🔎 No search result found for "
            f"your query `{query}`"
        )

    buttons.append([
        InlineKeyboardButton(
            "Close ❌",
            callback_data="close"
        )
    ])

    await send_msg.edit(
        text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        )
    )