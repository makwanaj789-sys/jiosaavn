import os
import random
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
from pytgcalls.types import MediaStream, Update, AudioQuality
from pytgcalls.types.stream import StreamEnded

from jiosaavn.bot import Bot
from jiosaavn.assistant import Assistant
from api.search_engine import SearchEngine
from api.thumbnail import generate_now_playing_card
from api.favorites import FavoritesManager
from api.local_cache import LocalCacheManager

logger = logging.getLogger(__name__)

assistant_client: Assistant = None

queues = defaultdict(list)
active_chats = set()
paused_chats = set()
now_playing_msg = {}

last_action_user = {}
now_playing_song = {}


def set_assistant(app: Assistant):
    global assistant_client
    assistant_client = app

    @app.call_py.on_update(pytgcalls_filters.stream_end)
    async def on_stream_end(client, update: Update):
        logger.info(f"🔔 STREAM_END EVENT FIRED: chat_id={getattr(update, 'chat_id', 'N/A')}, type={type(update)}")
        if isinstance(update, StreamEnded):
            chat_id = update.chat_id
            logger.info(f"🔔 Queue for {chat_id}: {[s['title'] for s in queues[chat_id]]}")
            await play_next(chat_id)
        else:
            logger.warning(f"🔔 Update was NOT StreamEnded instance: {update}")


async def get_song_ready(query: str, db):
    engine = SearchEngine()
    response = await engine.search(query)
    results = response.get("results", [])

    if not results:
        return None

    video_id = results[0]["id"]
    title = results[0].get("title", "Unknown")
    duration = results[0].get("duration", 0)
    uploader = results[0].get("uploader", "Unknown Artist")
    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

    local_cache = LocalCacheManager(db)
    cached_path = await local_cache.get(video_id)

    if cached_path:
        filepath = cached_path
        logger.info(f"⚡ MONGO LOCAL CACHE HIT: {title}")
    else:
        result = await engine.download_song(video_id)
        if not result or not result.get("success"):
            return None
        filepath = result["data"]["filepath"]
        filepath = await local_cache.save(video_id, filepath)

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
        ],
        [
            InlineKeyboardButton("🔵 Queue", callback_data="vc_queue"),
            InlineKeyboardButton("❤️ Favorite", callback_data="vc_fav")
        ],
        [
            InlineKeyboardButton("⏹️ Stop", callback_data="vc_stop"),
        ]
    ])


async def send_now_playing_card(client: Bot, chat_id: int, song: dict, started_by: str = None):
    caption = (
        f"🎧 **Now Playing**\n\n"
        f"🎵 **{song['title']}**\n"
        f"👤 {song.get('uploader', 'Unknown')}\n"
        f"⏱ {format_duration(song.get('duration'))}"
    )

    if started_by:
        caption += f"\n\n🎚 **Started by:** {started_by}"

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
        now_playing_song[chat_id] = song
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
        now_playing_song.pop(chat_id, None)
        try:
            await assistant_client.call_py.leave_call(chat_id)
        except Exception:
            pass
        return

    song = queues[chat_id].pop(0)

    try:
        await assistant_client.call_py.play(
            chat_id,
            MediaStream(
                song["filepath"],
                audio_parameters=AudioQuality.STUDIO
            )
        )
        active_chats.add(chat_id)
        paused_chats.discard(chat_id)
        if assistant_client.bot_ref:
            started_by = last_action_user.get(chat_id, {}).get("play")
            await send_now_playing_card(assistant_client.bot_ref, chat_id, song, started_by)
        logger.info(f"✅ VC AUTO-PLAYING NEXT: {song['title']} in {chat_id}")
    except Exception as e:
        logger.error(f"play_next error: {e}")


def user_mention(message_or_callback):
    user = message_or_callback.from_user
    if not user:
        return "Unknown"
    return f"[{user.first_name}](tg://user?id={user.id})"


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
    requester = user_mention(message)

    status_msg = await message.reply("🔎 **Searching & preparing your track...**")

    try:
        song = await get_song_ready(query, client.db)
        if not song:
            await status_msg.edit_text("❌ **Couldn't find or download that song.**")
            return

        active_calls = await assistant_client.call_py.calls
        is_actually_active = chat_id in active_calls

        if is_actually_active:
            queues[chat_id].append(song)
            await status_msg.edit_text(
                f"➕ **Added to Queue!**\n\n"
                f"🎵 **Track:** {song['title']}\n"
                f"📍 **Position:** #{len(queues[chat_id])}\n"
                f"👤 **Added by:** {requester}"
            )
            return

        active_chats.discard(chat_id)

        await status_msg.edit_text("📞 **Joining voice chat...**")

        await assistant_client.call_py.play(
            chat_id,
            MediaStream(
                song["filepath"],
                audio_parameters=AudioQuality.STUDIO
            )
        )

        active_chats.add(chat_id)
        last_action_user.setdefault(chat_id, {})["play"] = requester
        await status_msg.delete()

        await send_now_playing_card(client, chat_id, song, requester)
        logger.info(f"✅ VC PLAYING: {song['title']} in chat {chat_id}")

    except Exception as e:
        logger.error(f"voice_play error: {e}")
        await status_msg.edit_text(f"❌ **Error:** `{e}`")


@Bot.on_message(filters.command("shuffle") & filters.group)
async def voice_shuffle(client: Bot, message: Message):
    if not assistant_client or not assistant_client.call_py:
        await message.reply("🚫 **Voice chat engine isn't ready yet.**")
        return

    chat_id = message.chat.id
    requester = user_mention(message)

    favorites = FavoritesManager(client.db)
    fav_songs = await favorites.list_favorites(message.from_user.id, limit=50)

    if not fav_songs:
        await message.reply("💔 **Your favorites list is empty.**\n\nAdd some songs first using the ❤️ button!")
        return

    status_msg = await message.reply("🔀 **Shuffling your favorites...**")

    try:
        picked = random.choice(fav_songs)
        video_id = picked["video_id"]
        title = picked["title"]

        local_cache = LocalCacheManager(client.db)
        cached_path = await local_cache.get(video_id)

        if cached_path:
            filepath = cached_path
        else:
            engine = SearchEngine()
            result = await engine.download_song(video_id)
            if not result or not result.get("success"):
                await status_msg.edit_text("❌ **Couldn't download that track.**")
                return
            filepath = result["data"]["filepath"]
            filepath = await local_cache.save(video_id, filepath)

        song = {
            "video_id": video_id,
            "title": title,
            "duration": 0,
            "uploader": picked.get("uploader", "Unknown"),
            "filepath": filepath,
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
        }

        active_calls = await assistant_client.call_py.calls
        is_actually_active = chat_id in active_calls

        if is_actually_active:
            queues[chat_id].append(song)
            await status_msg.edit_text(
                f"🔀 **Shuffled in!**\n\n"
                f"🎵 {song['title']}\n"
                f"📍 Position: #{len(queues[chat_id])}"
            )
            return

        active_chats.discard(chat_id)
        await status_msg.edit_text("📞 **Joining voice chat...**")

        await assistant_client.call_py.play(
            chat_id,
            MediaStream(song["filepath"], audio_parameters=AudioQuality.STUDIO)
        )

        active_chats.add(chat_id)
        started_by = f"{requester} (🔀 shuffle)"
        last_action_user.setdefault(chat_id, {})["play"] = started_by
        await status_msg.delete()

        await send_now_playing_card(client, chat_id, song, started_by)
        logger.info(f"✅ SHUFFLE PLAYING: {song['title']} in chat {chat_id}")

    except Exception as e:
        logger.error(f"voice_shuffle error: {e}")
        await status_msg.edit_text(f"❌ **Error:** `{e}`")


@Bot.on_callback_query(filters.regex(r"^vc_pause$"))
async def cb_pause(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        await assistant_client.call_py.pause(chat_id)
        paused_chats.add(chat_id)
        last_action_user.setdefault(chat_id, {})["pause"] = user_mention(callback)
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
    skipper = user_mention(callback)
    await callback.answer("⏭️ Skipping...")

    if not queues[chat_id]:
        await callback.message.reply(f"📭 **Queue is empty.** Skipped by {skipper}")
        try:
            await assistant_client.call_py.leave_call(chat_id)
            active_chats.discard(chat_id)
            paused_chats.discard(chat_id)
            now_playing_song.pop(chat_id, None)
        except Exception:
            pass
        old_msg = now_playing_msg.pop(chat_id, None)
        if old_msg:
            try:
                await old_msg.delete()
            except Exception:
                pass
        return

    last_action_user.setdefault(chat_id, {})["play"] = f"{skipper} (skipped)"
    await play_next(chat_id)


@Bot.on_callback_query(filters.regex(r"^vc_stop$"))
async def cb_stop(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    stopper = user_mention(callback)
    queues[chat_id].clear()
    active_chats.discard(chat_id)
    paused_chats.discard(chat_id)
    now_playing_song.pop(chat_id, None)

    try:
        await assistant_client.call_py.leave_call(chat_id)
        await callback.answer("⏹️ Stopped")
        try:
            await callback.message.edit_caption(
                (callback.message.caption or "") + f"\n\n⏹️ **Stopped by:** {stopper}",
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


@Bot.on_callback_query(filters.regex(r"^vc_fav$"))
async def cb_fav(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    song = now_playing_song.get(chat_id)

    if not song:
        await callback.answer("❌ Nothing is playing right now.", show_alert=True)
        return

    try:
        favorites = FavoritesManager(client.db)
        await favorites.add(
            user_id=user_id,
            video_id=song["video_id"],
            title=song["title"],
            file_id="",
            uploader=song.get("uploader", "")
        )
        await callback.answer(f"❤️ '{song['title'][:30]}' added to your favorites!", show_alert=False)
    except Exception as e:
        logger.error(f"cb_fav error: {e}")
        await callback.answer(f"❌ {e}", show_alert=True)


@Bot.on_message(filters.command("vskip") & filters.group)
async def voice_skip(client: Bot, message: Message):
    chat_id = message.chat.id

    if not queues[chat_id]:
        await message.reply("📭 **Queue is empty, nothing to skip to.**")
        try:
            await assistant_client.call_py.leave_call(chat_id)
            active_chats.discard(chat_id)
            paused_chats.discard(chat_id)
            now_playing_song.pop(chat_id, None)
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
    now_playing_song.pop(chat_id, None)

    try:
        await assistant_client.call_py.leave_call(chat_id)
        await message.reply(f"⏹️ **Left the voice chat.** Queue cleared by {user_mention(message)}")
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