# songs_handler.py

import logging
import traceback

from api.search_engine import SearchEngine
from jiosaavn.bot import Bot

from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

logger = logging.getLogger(__name__)


# =========================================================
# SONG CALLBACK HANDLER
# =========================================================

@Bot.on_callback_query(filters.regex(r"^(song|youtube|album|playlist|artist)#"))
async def handle_song_callback(
    client: Bot,
    callback_query: CallbackQuery
):
    """Handle song/album/playlist/artist selection."""
    
    logger.info(f"📥 Callback received: {callback_query.data}")
    
    try:
        # Answer callback
        await callback_query.answer()
        
        # Parse callback data
        data_parts = callback_query.data.split("#")
        
        if len(data_parts) < 2:
            return await callback_query.message.edit_text(
                "❌ Invalid data received."
            )
        
        callback_type = data_parts[0]
        item_id = data_parts[1]
        
        logger.info(f"📌 Type: {callback_type}, ID: {item_id}")
        
        # Show loading
        await callback_query.message.edit_text(
            "__**Loading... ⏳**__"
        )
        
        # Initialize search engine
        engine = SearchEngine()
        
        # =============================================
        # HANDLE DIFFERENT TYPES
        # =============================================
        
        try:
            if callback_type == "youtube":
                await handle_youtube_song(callback_query, engine, item_id)
                
            elif callback_type == "song":
                await handle_jiosaavn_song(callback_query, engine, item_id)
                
            elif callback_type == "album":
                await handle_album(callback_query, engine, item_id)
                
            elif callback_type == "playlist":
                await handle_playlist(callback_query, engine, item_id)
                
            elif callback_type == "artist":
                await handle_artist(callback_query, engine, item_id)
                
            else:
                await callback_query.message.edit_text(
                    f"❌ Unknown type: {callback_type}"
                )
                
        except Exception as e:
            logger.exception(f"Error processing {callback_type}: {e}")
            await callback_query.message.edit_text(
                f"❌ Failed to load.\n\n"
                f"`{type(e).__name__}: {e}`"
            )
            
    except Exception as e:
        logger.exception("Error in callback handler")
        try:
            await callback_query.message.edit_text(
                f"❌ Something went wrong.\n\n"
                f"`{type(e).__name__}: {e}`"
            )
        except:
            pass


# =========================================================
# YOUTUBE SONG
# =========================================================

async def handle_youtube_song(callback_query, engine, video_id):
    """Handle YouTube song selection."""
    
    try:
        # Get YouTube video info
        song_data = await engine.get_song(
            item_id=video_id,
            source="youtube"
        )
        
        if not song_data:
            return await callback_query.message.edit_text(
                "❌ This YouTube video could not be found."
            )
        
        # Format song data
        formatted = format_youtube_song(song_data)
        
        # Create message
        text = create_song_text(formatted, is_youtube=True)
        
        # Create buttons
        buttons = [
            [
                InlineKeyboardButton(
                    "▶️ Play on YouTube",
                    url=f"https://youtu.be/{video_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎵 Download Audio",
                    callback_data=f"download#youtube#{video_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.exception(f"YouTube song error: {e}")
        raise


# =========================================================
# JIOSAAVN SONG
# =========================================================

async def handle_jiosaavn_song(callback_query, engine, song_id):
    """Handle JioSaavn song selection."""
    
    try:
        # Get JioSaavn song info
        song_data = await engine.get_song(
            item_id=song_id,
            source="jiosaavn"
        )
        
        if not song_data:
            return await callback_query.message.edit_text(
                "❌ This song could not be found."
            )
        
        # Format song data
        formatted = format_jiosaavn_song(song_data)
        
        # Create message
        text = create_song_text(formatted, is_youtube=False)
        
        # Create buttons
        buttons = [
            [
                InlineKeyboardButton(
                    "🎵 Download Audio",
                    callback_data=f"download#jiosaavn#{song_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.exception(f"JioSaavn song error: {e}")
        raise


# =========================================================
# ALBUM
# =========================================================

async def handle_album(callback_query, engine, album_id):
    """Handle album selection."""
    
    try:
        album_data = await engine.get_playlist_or_album(
            album_id=album_id
        )
        
        if not album_data:
            return await callback_query.message.edit_text(
                "❌ This album could not be found."
            )
        
        title = album_data.get("title", "Unknown Album")
        artist = album_data.get("artist", "Unknown Artist")
        songs = album_data.get("songs", [])
        
        text = f"""
**📚 {title}**

**👨‍🎤 Artist:** {artist}
**🎵 Total Songs:** {len(songs)}

__Songs in this album:__
"""
        
        for i, song in enumerate(songs[:10], 1):
            song_title = song.get("title", "Unknown")
            text += f"\n{i}. {song_title}"
        
        if len(songs) > 10:
            text += f"\n\n_...and {len(songs) - 10} more songs_"
        
        buttons = [
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.exception(f"Album error: {e}")
        raise


# =========================================================
# PLAYLIST
# =========================================================

async def handle_playlist(callback_query, engine, playlist_id):
    """Handle playlist selection."""
    
    try:
        playlist_data = await engine.get_playlist_or_album(
            playlist_id=playlist_id
        )
        
        if not playlist_data:
            return await callback_query.message.edit_text(
                "❌ This playlist could not be found."
            )
        
        title = playlist_data.get("title", "Unknown Playlist")
        creator = playlist_data.get("creator", "Unknown Creator")
        songs = playlist_data.get("songs", [])
        
        text = f"""
**💾 {title}**

**👤 Creator:** {creator}
**🎵 Total Songs:** {len(songs)}

__Songs in this playlist:__
"""
        
        for i, song in enumerate(songs[:10], 1):
            song_title = song.get("title", "Unknown")
            text += f"\n{i}. {song_title}"
        
        if len(songs) > 10:
            text += f"\n\n_...and {len(songs) - 10} more songs_"
        
        buttons = [
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.exception(f"Playlist error: {e}")
        raise


# =========================================================
# ARTIST
# =========================================================

async def handle_artist(callback_query, engine, artist_id):
    """Handle artist selection."""
    
    try:
        artist_data = await engine.get_artist(
            artist_id=artist_id
        )
        
        if not artist_data:
            return await callback_query.message.edit_text(
                "❌ This artist could not be found."
            )
        
        name = artist_data.get("name", "Unknown Artist")
        songs = artist_data.get("songs", [])
        
        text = f"""
**👨‍🎤 {name}**

**🎵 Total Songs:** {len(songs)}

__Popular songs:__
"""
        
        for i, song in enumerate(songs[:10], 1):
            song_title = song.get("title", "Unknown")
            text += f"\n{i}. {song_title}"
        
        if len(songs) > 10:
            text += f"\n\n_...and {len(songs) - 10} more songs_"
        
        buttons = [
            [
                InlineKeyboardButton(
                    "Close ❌",
                    callback_data="close"
                )
            ]
        ]
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.exception(f"Artist error: {e}")
        raise


# =========================================================
# FORMAT FUNCTIONS
# =========================================================

def format_youtube_song(song_data):
    """Format YouTube song data."""
    
    if not song_data:
        return None
    
    video_id = song_data.get("id", "")
    title = song_data.get("title", "Unknown Title")
    uploader = song_data.get("uploader", "Unknown Artist")
    duration = song_data.get("duration", 0)
    thumbnail = song_data.get("thumbnail", "")
    
    if duration:
        minutes = duration // 60
        seconds = duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
    else:
        duration_str = "N/A"
    
    return {
        "id": video_id,
        "title": title,
        "name": uploader,
        "more_info": {
            "album": uploader,
            "duration": duration_str,
            "year": "YouTube"
        },
        "source": "youtube",
        "url": f"https://youtu.be/{video_id}",
        "thumbnail": thumbnail,
        "type": "song"
    }


def format_jiosaavn_song(song_data):
    """Format JioSaavn song data."""
    
    if not song_data:
        return None
    
    return song_data


def create_song_text(song_data, is_youtube=False):
    """Create formatted song text."""
    
    if not song_data:
        return "❌ Song data not available."
    
    title = song_data.get("title", "Unknown Title")
    artist = song_data.get("name", "Unknown Artist")
    
    more_info = song_data.get("more_info", {})
    album = more_info.get("album", "N/A")
    duration = more_info.get("duration", "N/A")
    year = more_info.get("year", "N/A")
    
    source_emoji = "▶️" if is_youtube else "🎵"
    source_name = "YouTube" if is_youtube else "JioSaavn"
    
    text = f"""
**🎵 {title}**

**👨‍🎤 Artist:** {artist}
**💿 Album:** {album}
**⏱️ Duration:** {duration}
**📅 Year:** {year}
**📡 Source:** {source_emoji} {source_name}

_🎧 This track was picked by AartiMusic Bot_
"""
    
    return text


# =========================================================
# CLOSE BUTTON HANDLER
# =========================================================

@Bot.on_callback_query(filters.regex(r"^close$"))
async def close_callback(client, callback_query):
    """Handle close button."""
    
    try:
        await callback_query.answer()
        await callback_query.message.delete()
    except Exception as e:
        logger.exception(f"Close error: {e}")


# =========================================================
# DOWNLOAD HANDLER
# =========================================================

@Bot.on_callback_query(filters.regex(r"^download#"))
async def download_callback(client, callback_query):
    """Handle download button."""
    
    try:
        await callback_query.answer()
        
        data_parts = callback_query.data.split("#")
        if len(data_parts) < 3:
            return
        
        source = data_parts[1]
        item_id = data_parts[2]
        
        await callback_query.message.edit_text(
            f"🔄 Downloading...\n\n"
            f"**Source:** {source}\n"
            f"**ID:** `{item_id}`\n\n"
            f"_Download feature coming soon..._"
        )
        
    except Exception as e:
        logger.exception(f"Download error: {e}")