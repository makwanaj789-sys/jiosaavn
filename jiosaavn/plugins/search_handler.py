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
# HELPERS
# =========================================================

def safe_text(value, default="Unknown"):
    """
    Convert None/other values safely to text.
    Prevents html.unescape(None) and similar errors.
    """
    if value is None:
        return default

    try:
        return html.unescape(str(value))
    except Exception:
        return default


def safe_dict(value):
    """Always return a dictionary."""
    return value if isinstance(value, dict) else {}


def safe_list(value):
    """Always return a list."""
    return value if isinstance(value, list) else []


# =========================================================
# FILTERS
# =========================================================

# PRIVATE:
# Normal text = search
# Commands/links/via_bot ignored
private_search_filter = (
    filters.text
    & filters.incoming
    & filters.private
    & ~filters.regex(r"^https?://")
    & ~filters.via_bot
    & ~filters.command([
        "start",
        "settings",
        "help",
        "about"
    ])
)


# GROUP:
# Only:
# /am song name
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

    send_msg = None

    try:

        # =================================================
        # NORMAL MESSAGE
        # =================================================

        if isinstance(message, Message):

            send_msg = await message.reply(
                "__**Processing... ⏳**__",
                quote=True
            )

            # =============================================
            # PRIVATE
            # =============================================

            if message.chat.type == "private":

                query = (
                    message.text or ""
                ).strip()

            # =============================================
            # GROUP
            # =============================================

            else:

                command = message.command or []

                if len(command) < 2:

                    return await send_msg.edit(
                        "❌ Please enter a song name.\n\n"
                        "**Example:**\n"
                        "`/am Alan Walker Spectre`"
                    )

                query = " ".join(
                    command[1:]
                ).strip()


            # =============================================
            # USER SETTINGS
            # =============================================

            try:

                user_data = await client.db.get_user(
                    message.from_user.id
                )

            except Exception:

                logger.exception(
                    "Failed to get user settings"
                )

                user_data = {}


            if not isinstance(user_data, dict):
                user_data = {}


            search_type = (
                user_data.get("type") or "all"
            )

            page_no = 1


        # =================================================
        # CALLBACK
        # =================================================

        else:

            await message.answer()

            send_msg = message.message

            data = (
                message.data or ""
            ).split("#")


            search_type = (
                data[1]
                if len(data) > 1 and data[1]
                else "all"
            )


            page_no = 1


            if len(data) >= 3:

                try:

                    page_no = int(
                        data[2]
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    page_no = 1


            # =============================================
            # GET ORIGINAL QUERY
            # =============================================

            reply_message = (
                message.message.reply_to_message
            )


            if (
                reply_message
                and reply_message.text
            ):

                query = (
                    reply_message.text or ""
                ).strip()


                # /am query
                if query.lower().startswith(
                    "/am"
                ):

                    parts = query.split(
                        maxsplit=1
                    )

                    if len(parts) == 2:

                        query = (
                            parts[1] or ""
                        ).strip()

                    else:

                        query = ""

            else:

                return await send_msg.edit(
                    "❌ Could not find the original "
                    "search query."
                )


        # =================================================
        # QUERY CHECK
        # =================================================

        if not query:

            return await send_msg.edit(
                "❌ Please enter a song name."
            )


        # =================================================
        # JIOSAAVN SEARCH
        # =================================================

        try:

            api = Jiosaavn()


            if search_type in (
                "all",
                "topquery"
            ):

                response = await api.search_all_types(
                    query=query
                )

            else:

                response = await api.search(
                    query=query,
                    search_type=search_type,
                    page_no=page_no
                )


        except RuntimeError as e:

            logger.error(
                "JioSaavn API RuntimeError: %s",
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
                "JioSaavn search request failed"
            )

            traceback.print_exc()

            return await send_msg.edit(
                "❌ Search failed.\n\n"
                f"`{type(e).__name__}: {e}`"
            )


        # =================================================
        # RESPONSE VALIDATION
        # =================================================

        if not response:

            return await send_msg.edit(
                "🔎 No search result found for "
                f"your query `{query}`"
            )


        if not isinstance(response, dict):

            logger.error(
                "Unexpected API response: %r",
                response
            )

            return await send_msg.edit(
                "❌ Invalid response received "
                "from JioSaavn."
            )


        buttons = []


        # =================================================
        # ALL / TOPQUERY
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

                topquery = safe_dict(
                    response.get("topquery")
                )

                topquery_data = safe_list(
                    topquery.get("data")
                )


                # Remove invalid entries
                valid_topquery = [

                    item

                    for item in topquery_data

                    if isinstance(
                        item,
                        dict
                    )
                ]


                try:

                    sub_sorted_data = sorted(

                        valid_topquery,

                        key=lambda x: (
                            x.get("position")
                            or 0
                        )
                    )

                except Exception:

                    sub_sorted_data = (
                        valid_topquery
                    )


                for item in sub_sorted_data:

                    title = safe_text(
                        item.get("title")
                    )


                    album = safe_text(
                        item.get("album"),
                        ""
                    )


                    item_type = safe_text(
                        item.get("type"),
                        ""
                    ).lower()


                    item_url = safe_text(
                        item.get("url"),
                        ""
                    )


                    if not item_url:
                        continue


                    item_id = (
                        item_url
                        .rstrip("/")
                        .rsplit("/", 1)[-1]
                    )


                    if not item_id:
                        continue


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

                valid_items = []


                for (
                    result_type,
                    result
                ) in response.items():

                    if not isinstance(
                        result,
                        dict
                    ):
                        continue

                    valid_items.append(
                        (
                            result_type,
                            result
                        )
                    )


                try:

                    sorted_data = sorted(

                        valid_items,

                        key=lambda value: (
                            value[1].get(
                                "position"
                            )
                            or 0
                        )
                    )

                except Exception:

                    sorted_data = (
                        valid_items
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


                    data = safe_list(
                        result.get("data")
                    )


                    if not data:
                        continue


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
        # SONG / ALBUM / PLAYLIST / ARTIST
        # =================================================

        else:

            total_results = (
                response.get("total") or 0
            )


            try:

                total_results = int(
                    total_results
                )

            except (
                ValueError,
                TypeError
            ):

                total_results = 0


            results = safe_list(
                response.get("results")
            )


            for result in results:

                if not isinstance(
                    result,
                    dict
                ):

                    continue


                # =========================================
                # ITEM URL / ID
                # =========================================

                perma_url = safe_text(
                    result.get("perma_url"),
                    ""
                )


                if not perma_url:
                    continue


                item_id = (
                    perma_url
                    .rstrip("/")
                    .rsplit("/", 1)[-1]
                )


                if not item_id:
                    continue


                # =========================================
                # TITLE
                # =========================================

                title = safe_text(
                    result.get("title")
                )


                # =========================================
                # RESULT TYPE
                # =========================================

                result_type = safe_text(
                    result.get("type"),
                    ""
                ).lower()


                # =========================================
                # ARTIST
                # =========================================

                artist = safe_text(
                    result.get("name"),
                    "Unknown"
                )


                # =========================================
                # MORE INFO
                # =========================================

                more_info = safe_dict(
                    result.get("more_info")
                )


                album = safe_text(
                    more_info.get("album"),
                    ""
                )


                # =========================================
                # BUTTON LABEL
                # =========================================

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


                if not button_label:
                    continue


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
            # RESULT TEXT
            # =============================================

            text = (
                f"**📈 Total Results:** "
                f"{total_results}\n\n"
                f"**🔍 Search Query:** "
                f"{query}\n\n"
                f"**📜 Page No:** "
                f"{page_no}"
            )


            # =============================================
            # PAGINATION
            # =============================================

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


            if (
                total_results
                > (10 * page_no)
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
        # NO RESULTS
        # =================================================

        if not buttons:

            return await send_msg.edit(
                "🔎 No search result found for "
                f"your query `{query}`"
            )


        # =================================================
        # CLOSE
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
        # SHOW RESULTS
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

            if send_msg:

                await send_msg.edit(
                    "❌ Something went wrong.\n\n"
                    f"`{type(e).__name__}: {e}`"
                )

        except Exception:

            logger.exception(
                "Failed to display search error"
            )