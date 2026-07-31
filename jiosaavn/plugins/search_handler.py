import html
import logging
import traceback

from api.search_engine import SearchEngine
from jiosaavn.bot import Bot

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

# Post Creator state check
from jiosaavn.plugins.admin import is_post_creator_active


logger = logging.getLogger(__name__)


# =========================================================
# SAFE HELPERS
# =========================================================

def safe_text(value, default="Unknown"):
    """Safely convert API values to text."""

    if value is None:
        return default

    try:
        return html.unescape(str(value))
    except Exception:
        return default


def safe_dict(value):
    """Always return dict."""
    return value if isinstance(value, dict) else {}


def safe_list(value):
    """Always return list."""
    return value if isinstance(value, list) else []


# =========================================================
# FILTERS
# =========================================================

# PRIVATE:
# Normal text directly searches music.
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
        "about",
        "admin",
        "cancel"
    ])
)


# GROUP:
# Only /am SONG NAME will trigger search.
group_search_filter = (
    filters.command("am")
    & filters.incoming
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

            # =============================================
            # POST CREATOR PROTECTION
            # =============================================

            if (
                message.from_user
                and is_post_creator_active(
                    message.from_user.id
                )
            ):
                return

            send_msg = await message.reply(
                "__**Processing... ⏳**__",
                quote=True
            )

            raw_text = (
                message.text or ""
            ).strip()

            # =============================================
            # PRIVATE CHAT
            # =============================================

            if (
                message.chat.type
                == ChatType.PRIVATE
            ):

                query = raw_text

            # =============================================
            # GROUP / SUPERGROUP
            # =============================================

            else:

                parts = raw_text.split(
                    maxsplit=1
                )

                if len(parts) < 2:

                    return await send_msg.edit(
                        "❌ Please enter a song name.\n\n"
                        "**Example:**\n"
                        "`/am Alan Walker Spectre`"
                    )

                query = parts[1].strip()

                if not query:

                    return await send_msg.edit(
                        "❌ Please enter a song name.\n\n"
                        "**Example:**\n"
                        "`/am Alan Walker Spectre`"
                    )

            # =============================================
            # GET USER SETTINGS
            # =============================================

            try:

                user_data = (
                    await client.db.get_user(
                        message.from_user.id
                    )
                )

            except Exception:

                logger.exception(
                    "Failed to get user settings"
                )

                user_data = {}

            if not isinstance(
                user_data,
                dict
            ):
                user_data = {}

            search_type = (
                user_data.get("type")
                or "all"
            )

            page_no = 1

        # =================================================
        # CALLBACK QUERY
        # =================================================

        else:

            await message.answer()

            send_msg = message.message

            callback_data = (
                message.data or ""
            )

            data = callback_data.split("#")

            search_type = (
                data[1]
                if len(data) > 1
                and data[1]
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
            # FIND ORIGINAL SEARCH QUERY
            # =============================================

            reply_message = (
                message
                .message
                .reply_to_message
            )

            if (
                reply_message
                and reply_message.text
            ):

                query = (
                    reply_message.text
                    or ""
                ).strip()

                if query.lower().startswith(
                    "/am"
                ):

                    parts = query.split(
                        maxsplit=1
                    )

                    if len(parts) >= 2:

                        query = (
                            parts[1]
                            .strip()
                        )

                    else:

                        query = ""

            else:

                return await send_msg.edit(
                    "❌ Could not find the "
                    "original search query."
                )

        # =================================================
        # EMPTY QUERY CHECK
        # =================================================

        if not query:

            return await send_msg.edit(
                "❌ Please enter a song name."
            )

        # =================================================
        # ADMIN ANALYTICS
        # =================================================

        if isinstance(message, Message):

            try:

                user_id = (
                    message.from_user.id
                    if message.from_user
                    else 0
                )

                chat_id = (
                    message.chat.id
                )

                if user_id:

                    await client.db.get_user(
                        user_id
                    )

                    await client.db.add_search(
                        user_id=user_id,
                        chat_id=chat_id
                    )

                if (
                    message.chat.type
                    in (
                        ChatType.GROUP,
                        ChatType.SUPERGROUP
                    )
                ):

                    await client.db.add_group(
                        chat_id
                    )

            except Exception:

                logger.exception(
                    "Failed to save "
                    "search analytics"
                )

        # =================================================
        # SEARCH ENGINE - YOUTUBE FIRST
        # =================================================

        try:

            engine = SearchEngine()

            # Try YouTube search first
            logger.info(f"Searching YouTube for: {query}")
            
            response = await engine.search(
                query=query,
                source="youtube",
                search_type=search_type,
                page_no=page_no
            )

            # Check if YouTube returned results
            has_results = False
            
            if isinstance(response, dict):
                if search_type in ("all", "topquery"):
                    songs_data = safe_list(
                        response.get("songs", {}).get("data", [])
                    )
                    if songs_data:
                        has_results = True
                else:
                    results_data = safe_list(
                        response.get("results", [])
                    )
                    if results_data:
                        has_results = True
                    else:
                        for key in response:
                            if key not in ["total", "position"]:
                                data = safe_list(
                                    response.get(key, {}).get("data", [])
                                )
                                if data:
                                    has_results = True
                                    break

            # =============================================
            # FALLBACK TO JIOSAAVN IF NO RESULTS
            # =============================================
            
            if not has_results:
                logger.info(f"No YouTube results for '{query}'. Falling back to JioSaavn.")
                
                response = await engine.search(
                    query=query,
                    source="jiosaavn",
                    search_type=search_type,
                    page_no=page_no
                )

        except Exception as e:
            logger.exception(f"YouTube search failed: {e}")
            
            # Try JioSaavn as fallback
            try:
                logger.info(f"Falling back to JioSaavn for '{query}'")
                response = await engine.search(
                    query=query,
                    source="jiosaavn",
                    search_type=search_type,
                    page_no=page_no
                )
            except Exception as fallback_error:
                logger.exception(f"JioSaavn fallback also failed: {fallback_error}")
                return await send_msg.edit(
                    f"❌ Search failed on both YouTube and JioSaavn.\n\n"
                    f"`{type(fallback_error).__name__}: {fallback_error}`"
                )

        # =================================================
        # RESPONSE VALIDATION
        # =================================================

        if not response:

            return await send_msg.edit(
                "🔎 No search result found "
                f"for your query `{query}`"
            )

        if not isinstance(
            response,
            dict
        ):

            logger.error(
                "Invalid API response: %r",
                response
            )

            return await send_msg.edit(
                "❌ Invalid response received "
                "from API."
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
                    response.get(
                        "topquery"
                    )
                )

                topquery_data = safe_list(
                    topquery.get(
                        "data"
                    )
                )

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
                            x.get(
                                "position"
                            )
                            or 0
                        )
                    )

                except Exception:

                    sub_sorted_data = (
                        valid_topquery
                    )

                for item in sub_sorted_data:

                    title = safe_text(
                        item.get(
                            "title"
                        )
                    )

                    album = safe_text(
                        item.get(
                            "album"
                        ),
                        ""
                    )

                    item_type = safe_text(
                        item.get(
                            "type"
                        ),
                        ""
                    ).lower()

                    item_url = safe_text(
                        item.get(
                            "url"
                        ),
                        ""
                    )

                    if not item_url:
                        continue

                    item_id = (
                        item_url
                        .rstrip("/")
                        .rsplit(
                            "/",
                            1
                        )[-1]
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
                            f"{emoji} "
                            f"{title} "
                            f"from {album}"
                        )

                    else:

                        button_text = (
                            f"{emoji} "
                            f"{title}"
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

                    if result_type in ["total", "position"]:
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

                    data_list = safe_list(
                        result.get(
                            "data"
                        )
                    )

                    if not data_list:
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
        # SONG / ALBUM / PLAYLIST / ARTIST RESULTS
        # =================================================

        else:

            total_results = (
                response.get("total")
                or 0
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
            
            # If no results, try to get from nested structure
            if not results:
                for key in response:
                    if key not in ["total", "position"]:
                        nested_data = safe_list(
                            response.get(key, {}).get("data", [])
                        )
                        if nested_data:
                            results = nested_data
                            break

            for result in results:

                if not isinstance(
                    result,
                    dict
                ):
                    continue

                # =========================================
                # URL / ID
                # =========================================

                perma_url = safe_text(
                    result.get(
                        "perma_url"
                    ),
                    ""
                )

                if not perma_url:
                    perma_url = safe_text(
                        result.get(
                            "url"
                        ),
                        ""
                    )

                if not perma_url:
                    continue

                item_id = (
                    perma_url
                    .rstrip("/")
                    .rsplit(
                        "/",
                        1
                    )[-1]
                )

                if not item_id:
                    continue

                # =========================================
                # TITLE
                # =========================================

                title = safe_text(
                    result.get(
                        "title"
                    )
                )

                # =========================================
                # TYPE
                # =========================================

                result_type = safe_text(
                    result.get(
                        "type"
                    ),
                    "song"
                ).lower()

                # =========================================
                # ARTIST
                # =========================================

                artist = safe_text(
                    result.get(
                        "name"
                    ),
                    "Unknown"
                )

                if artist == "Unknown":
                    artist = safe_text(
                        result.get(
                            "artist"
                        ),
                        "Unknown"
                    )
                    if artist == "Unknown":
                        artist = safe_text(
                            result.get(
                                "uploader"
                            ),
                            "Unknown"
                        )

                # =========================================
                # MORE INFO
                # =========================================

                more_info = safe_dict(
                    result.get(
                        "more_info"
                    )
                )

                album = safe_text(
                    more_info.get(
                        "album"
                    ),
                    ""
                )

                if not album and artist != "Unknown":
                    album = artist

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
                    button_label = f"🎙 {title}"

                # =========================================
                # ⭐ DETERMINE SOURCE FOR CALLBACK
                # =========================================

                is_youtube = False
                
                # Check 1: Source field
                if result.get("source") == "youtube":
                    is_youtube = True
                
                # Check 2: URL contains youtube
                elif "youtube.com" in perma_url or "youtu.be" in perma_url:
                    is_youtube = True
                
                # Check 3: URL field contains youtube
                elif "youtube.com" in result.get("url", "") or "youtu.be" in result.get("url", ""):
                    is_youtube = True
                
                # Check 4: Video ID format (11 alphanumeric characters)
                elif len(item_id) == 11 and item_id.isalnum():
                    if result.get("source") != "jiosaavn":
                        is_youtube = True

                # Set callback type
                if is_youtube:
                    callback_type = "youtube"
                    logger.info(f"🎯 YouTube detected: {title} -> {item_id}")
                else:
                    callback_type = result_type
                    logger.info(f"🎯 JioSaavn detected: {title} -> {item_id}")

                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=button_label,
                            callback_data=(
                                f"{callback_type}#"
                                f"{item_id}"
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
        # NO RESULTS
        # =================================================

        if not buttons:

            return await send_msg.edit(
                "🔎 No search result found "
                f"for your query `{query}`"
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
            reply_markup=(
                InlineKeyboardMarkup(
                    buttons
                )
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
                "Failed to display "
                "search error"
            )