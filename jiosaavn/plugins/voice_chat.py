import os
import logging
from collections import defaultdict
from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pytgcalls import filters as pytgcalls_filters
from pytgcalls.types import MediaStream, Update
from pytgcalls.types.stream import StreamEnded

from jiosaavn.bot import Bot
from jiosaavn.assistant import Assistant
from api.search_engine import SearchEngine
from api.thumbnail import generate_now_playing_card

logger = logging.getLogger(__name__)

assistant_client: Assistant = None

# Queue system: each chat has its own list of pending songs
queues = defaultdict(list)

# Tracks which chats currently have an active stream
active_chats = set()
paused_chats = set()
now_playing_msg = {}

# Local disk cache: video_id -> filepath (so we never re-download)
local_file_cache = {}


def set_assistant(app: Assistant):
    global assistant_client
    assistant_client = app

    @app.call_py.on_update(pytgcalls_filters.stream_end)
    async def on_stream_end(client, update: Update):
        if isinstance(update, StreamEnded):
            chat_id = update.chat_id
            await play_next(chat_id)


async def get_song_ready(query: str):
    """
    Returns song info with a guaranteed-downloaded local filepath.
    Uses local_file_cache to skip re-downloading if already fetched
    during this bot session.
    """
    engine = SearchEngine()
    response = await engine.search(query)
    results = response.get("results", [])

    if not results:
        return None

    video_id = results[0]["id"]
    title = results[0].get("title", "Unknown")
    duration = results[0].get("duration", 0)
    uploader = results[0].get("uploader", "Unknown Artist")
    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    if video_id in local_file_cache and os.path.exists(local_file_cache[video_id]):
        filepath = local_file_cache[video_id]
        logger.info(f"⚡ LOCAL CACHE HIT: {title}")
    else:
        result = await engine.download_song(video_id)
        if not result or not result.get("success"):
            return None
        filepath = result["data"]["filepath"]
        local_file_cache[video_id] = filepath

    return {
        "video_id": video_id,
        "title": title,
        "duration": duration,
        "uploader": uploader,
        "filepath": filepath,
        "thumbnail": thumbnail_url
    }


def format_duration(seconds):
    if not seconds:
        return "Live"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def now_playing_markup(is_paused=False):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "▶️ Resume" if is_paused else "⏸️ Pause",
                callback_data="vc_resume" if is_paused else "vc_pause"
            ),
            InlineKeyboardButton("⏭️ Skip", callback_data="vc_skip"),
            InlineKeyboardButton("⏹️ Stop", callback_data="vc_stop"),
        ],
        [
            InlineKeyboardButton("📋 Queue", callback_data="vc_queue")
        ]
    ])


async def send_now_playing_card(client: Bot, chat_id: int, song: dict):
    caption = (
        f"🎧 **Now Playing**\n\n"
        f"🎵 **{song['title']}**\n"
        f"👤 {song.get('uploader', 'Unknown')}\n"
        f"⏱ {format_duration(song.get('duration'))}"
    )

    card_path = generate_now_playing_card(
        song["thumbnail"], song["title"], song.get("uploader", "Unknown")
    )

    try:
        if card_path and os.path.exists(card_path):
            msg = await client.send_photo(
                chat_id=chat_id,
                photo=card_path,
                caption=caption,
                reply_markup=now_playing_markup()
            )
            os.remove(card_path)
        else:
            msg = await client.send_photo(
                chat_id=chat_id,
                photo=song["thumbnail"],
                caption=caption,
                reply_markup=now_playing_markup()
            )
        now_playing_msg[chat_id] = msg
    except Exception as e:
        logger.error(f"send_now_playing_card error: {e}")


async def play_next(chat_id: int):
    old_msg = now_playing_msg.pop(chat_id, None)
    if old_msg:
        try:
            await old_msg.delete()
        except Exception:
            pass

    if not queues[chat_id]:
        active_chats.discard(chat_id)
        paused_chats.discard(chat_id)
        try:
            await assistant_client.call_py.leave_call(chat_id)
        except Exception:
            pass
        return

    song = queues[chat_id].pop(0)

    try:
        await assistant_client.call_py.play(
            chat_id,
            MediaStream(song["filepath"])
        )
        active_chats.add(chat_id)
        paused_chats.discard(chat_id)
        if assistant_client.bot_ref:
            await send_now_playing_card(assistant_client.bot_ref, chat_id, song)
        logger.info(f"✅ VC AUTO-PLAYING NEXT: {song['title']} in {chat_id}")
    except Exception as e:
        logger.error(f"play_next error: {e}")


@Bot.on_message(filters.command("vplay") & filters.group)
async def voice_play(client: Bot, message: Message):
    if not assistant_client or not assistant_client.call_py:
        await message.reply("🚫 **Voice chat engine isn't ready yet.**")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "⚠️ **Please provide a song name.**\n\n"
            "✨ Example: `/vplay Alan Walker Faded`"
        )
        return

    query = parts[1].strip()
    chat_id = message.chat.id

    status_msg = await message.reply("🔎 **Searching & preparing your track...**")

    try:
        song = await get_song_ready(query)
        if not song:
            await status_msg.edit_text("❌ **Couldn't find or download that song.**")
            return

        # 🔥 FIX: real status check karo, sirf local set pe depend mat karo
        active_calls = await assistant_client.call_py.calls
        is_actually_active = chat_id in active_calls

        if is_actually_active:
            queues[chat_id].append(song)
            await status_msg.edit_text(
                f"➕ **Added to Queue!**\n\n"
                f"🎵 **Track:** {song['title']}\n"
                f"📍 **Position:** #{len(queues[chat_id])}\n"
                f"✅ Pre-downloaded, ready for instant playback"
            )
            return

        # Agar local set out-of-sync tha, clean kar do
        active_chats.discard(chat_id)

        await status_msg.edit_text("📞 **Joining voice chat...**")

        await assistant_client.call_py.play(
            chat_id,
            MediaStream(song["filepath"])
        )

        active_chats.add(chat_id)
        await status_msg.delete()

        await send_now_playing_card(client, chat_id, song)
        logger.info(f"✅ VC PLAYING: {song['title']} in chat {chat_id}")

    except Exception as e:
        logger.error(f"voice_play error: {e}")
        await status_msg.edit_text(f"❌ **Error:** `{e}`")


@Bot.on_callback_query(filters.regex(r"^vc_pause$"))
async def cb_pause(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        await assistant_client.call_py.pause(chat_id)
        paused_chats.add(chat_id)
        await callback.answer("⏸️ Paused")
        await callback.edit_message_reply_markup(now_playing_markup(is_paused=True))
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^vc_resume$"))
async def cb_resume(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        await assistant_client.call_py.resume(chat_id)
        paused_chats.discard(chat_id)
        await callback.answer("▶️ Resumed")
        await callback.edit_message_reply_markup(now_playing_markup(is_paused=False))
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^vc_skip$"))
async def cb_skip(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    await callback.answer("⏭️ Skipping...")

    if not queues[chat_id]:
        await callback.message.reply("📭 **Queue is empty, nothing to skip to.**")
        try:
            await assistant_client.call_py.leave_call(chat_id)
            active_chats.discard(chat_id)
            paused_chats.discard(chat_id)
        except Exception:
            pass
        old_msg = now_playing_msg.pop(chat_id, None)
        if old_msg:
            try:
                await old_msg.delete()
            except Exception:
                pass
        return

    await play_next(chat_id)


@Bot.on_callback_query(filters.regex(r"^vc_stop$"))
async def cb_stop(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    queues[chat_id].clear()
    active_chats.discard(chat_id)
    paused_chats.discard(chat_id)

    try:
        await assistant_client.call_py.leave_call(chat_id)
        await callback.answer("⏹️ Stopped")
        try:
            await callback.message.edit_caption(
                (callback.message.caption or "") + "\n\n⏹️ **Stopped.**",
                reply_markup=None
            )
        except Exception:
            pass
        now_playing_msg.pop(chat_id, None)
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^vc_queue$"))
async def cb_queue(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id

    if not queues[chat_id]:
        await callback.answer("📭 Queue is empty", show_alert=True)
        return

    text = "\n".join(
        f"{i}. {song['title']}" for i, song in enumerate(queues[chat_id], start=1)
    )
    await callback.answer(text[:200], show_alert=True)


@Bot.on_message(filters.command("vskip") & filters.group)
async def voice_skip(client: Bot, message: Message):
    chat_id = message.chat.id

    if not queues[chat_id]:
        await message.reply("📭 **Queue is empty, nothing to skip to.**")
        try:
            await assistant_client.call_py.leave_call(chat_id)
            active_chats.discard(chat_id)
            paused_chats.discard(chat_id)
        except Exception:
            pass
        return

    await message.reply("⏭️ **Skipping...**")
    await play_next(chat_id)


@Bot.on_message(filters.command("vstop") & filters.group)
async def voice_stop(client: Bot, message: Message):
    chat_id = message.chat.id
    queues[chat_id].clear()
    active_chats.discard(chat_id)
    paused_chats.discard(chat_id)

    try:
        await assistant_client.call_py.leave_call(chat_id)
        await message.reply("⏹️ **Left the voice chat.** Queue cleared.")
        now_playing_msg.pop(chat_id, None)
    except Exception as e:
        await message.reply(f"❌ **Error:** `{e}`")


@Bot.on_message(filters.command("vqueue") & filters.group)
async def voice_queue(client: Bot, message: Message):
    chat_id = message.chat.id

    if not queues[chat_id]:
        await message.reply("📭 **Queue is empty.**")
        return

    text = "📋 **Current Queue**\n\n"
    for i, song in enumerate(queues[chat_id], start=1):
        text += f"**{i}.** 🎵 {song['title']}\n"

    await message.reply(text)