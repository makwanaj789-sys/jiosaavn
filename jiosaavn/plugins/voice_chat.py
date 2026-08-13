import os
import random
import asyncio
import logging
import subprocess
from collections import defaultdict
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
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
monitor_tasks = {}
prefetch_tasks = {}
play_locks = defaultdict(asyncio.Lock)


def set_assistant(app: Assistant):
    global assistant_client
    assistant_client = app
    logger.info("🔧 set_assistant CALLED — assistant_client set")

    @app.call_py.on_update(pytgcalls_filters.stream_end)
    async def on_stream_end(client, update: Update):
        if isinstance(update, StreamEnded):
            chat_id = update.chat_id
            await play_next(chat_id)

    logger.info("🔧 on_stream_end handler registered")


async def is_admin(client: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER
        )
    except Exception as e:
        logger.warning(f"is_admin check failed for {user_id} in {chat_id}: {e}")
        return False


async def ensure_assistant_in_chat(client: Bot, chat_id: int) -> bool:
    try:
        assistant_id = (await assistant_client.app.get_me()).id
        logger.info(f"🔗 Checking if assistant {assistant_id} is in chat {chat_id}")

        needs_invite = False

        try:
            member = await client.get_chat_member(chat_id, assistant_id)
            logger.info(f"🔗 Assistant status in chat: {member.status}")

            if str(member.status) in ("ChatMemberStatus.BANNED", "ChatMemberStatus.LEFT"):
                logger.info(f"🔗 Assistant is {member.status}, attempting to unban...")
                try:
                    await client.unban_chat_member(chat_id, assistant_id)
                    logger.info("✅ Assistant unbanned")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Couldn't unban assistant: {e}")
                    return False
                needs_invite = True
            else:
                return True

        except Exception as e:
            logger.info(f"🔗 Assistant not in chat ({e}), will invite...")
            needs_invite = True

        if needs_invite:
            try:
                invite_link = await client.export_chat_invite_link(chat_id)
                logger.info("🔗 Generated invite link")
            except Exception as e:
                logger.error(f"❌ Couldn't generate invite link: {e}")
                return False

            try:
                await assistant_client.app.join_chat(invite_link)
                logger.info(f"✅ Assistant joined chat {chat_id}")
            except Exception as e:
                logger.error(f"❌ Assistant couldn't join: {e}")
                return False

            await asyncio.sleep(3)

        return True

    except Exception as e:
        logger.error(f"❌ ensure_assistant_in_chat failed for {chat_id}: {e}")
        return False


def get_audio_duration(filepath: str) -> int:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ],
            capture_output=True,
            text=True,
            timeout=15
        )
        duration = float(result.stdout.strip())
        return int(duration)
    except Exception as e:
        logger.warning(f"ffprobe duration error for {filepath}: {e}")
        return 0


def cancel_monitor(chat_id: int):
    task = monitor_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()


def cancel_prefetch(chat_id: int):
    task = prefetch_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()


async def prefetch_next_song(chat_id: int):
    try:
        if not queues[chat_id]:
            return

        next_song = queues[chat_id][0]

        if next_song.get("filepath"):
            return

        video_id = next_song["video_id"]
        logger.info(f"⏬ PREFETCH: starting background download for '{next_song['title']}'")

        db = assistant_client.bot_ref.db
        local_cache = LocalCacheManager(db)

        cached_path = await local_cache.get(video_id)
        if cached_path:
            next_song["filepath"] = cached_path
            logger.info(f"⏬ PREFETCH: cache hit for '{next_song['title']}'")
            return

        engine = SearchEngine()
        result = await engine.download_song(video_id)

        if result and result.get("success"):
            path = result["data"]["filepath"]
            next_song["filepath"] = await local_cache.save(video_id, path)
            logger.info(f"✅ PREFETCH: ready — '{next_song['title']}'")
        else:
            logger.warning(f"⚠️ PREFETCH failed for '{next_song['title']}'")

    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.error(f"PREFETCH error for chat {chat_id}: {e}")
    finally:
        prefetch_tasks.pop(chat_id, None)


def start_prefetch(chat_id: int):
    cancel_prefetch(chat_id)
    task = asyncio.create_task(prefetch_next_song(chat_id))
    prefetch_tasks[chat_id] = task


async def monitor_playback(chat_id: int, filepath: str):
    duration = get_audio_duration(filepath)

    if duration <= 0:
        logger.warning(f"🔍 MONITOR: couldn't determine duration for {filepath}, using fallback")
        duration = 300

    logger.info(f"🔍 MONITOR: watching chat {chat_id} for {duration}s")

    remaining = duration + 1
    tick = 1

    try:
        while remaining > 0:
            await asyncio.sleep(tick)

            if chat_id in paused_chats:
                continue

            remaining -= tick

            active_calls = await assistant_client.call_py.calls
            if chat_id not in active_calls:
                logger.info(f"🔍 MONITOR: chat {chat_id} left the call during playback")
                monitor_tasks.pop(chat_id, None)
                return

        logger.info(f"🔍 MONITOR: track finished in chat {chat_id}, moving to next")

    except asyncio.CancelledError:
        logger.info(f"🔍 MONITOR: cancelled for chat {chat_id}")
        return
    except Exception as e:
        logger.warning(f"🔍 MONITOR error for {chat_id}: {e}")

    monitor_tasks.pop(chat_id, None)
    await play_next(chat_id)


def start_monitor(chat_id: int, filepath: str):
    cancel_monitor(chat_id)
    task = asyncio.create_task(monitor_playback(chat_id, filepath))
    monitor_tasks[chat_id] = task


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
    youtube_url = f"https://youtube.com/watch?v={song['video_id']}"

    caption = (
        f"**◈ NOW STREAMING ◈**\n\n"
        f">🎵 [{song['title']}]({youtube_url})\n"
        f">👤 {song.get('uploader', 'Unknown')}"
    )

    if started_by:
        caption += f"\n>🎚 Requested by {started_by}"

    caption += "\n\n__♫ powered by AartiMusic ♫__"

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
            fallback_thumb = song["thumbnail"].replace("maxresdefault", "hqdefault")
            msg = await client.send_photo(
                chat_id=chat_id,
                photo=fallback_thumb,
                caption=caption,
                reply_markup=now_playing_markup()
            )
        now_playing_msg[chat_id] = msg
        now_playing_song[chat_id] = song
    except Exception as e:
        logger.error(f"send_now_playing_card error: {e}")
        try:
            msg = await client.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=now_playing_markup(),
                disable_web_page_preview=True
            )
            now_playing_msg[chat_id] = msg
            now_playing_song[chat_id] = song
        except Exception as e2:
            logger.error(f"Fallback text message also failed: {e2}")


async def play_next(chat_id: int):
    async with play_locks[chat_id]:
        old_msg = now_playing_msg.pop(chat_id, None)
        if old_msg:
            try:
                await old_msg.delete()
            except Exception:
                pass

        cancel_monitor(chat_id)

        while queues[chat_id]:
            song = queues[chat_id].pop(0)

            if not song.get("filepath"):
                try:
                    db = assistant_client.bot_ref.db
                    local_cache = LocalCacheManager(db)
                    cached_path = await local_cache.get(song["video_id"])

                    if cached_path:
                        song["filepath"] = cached_path
                    else:
                        engine = SearchEngine()
                        result = await engine.download_song(song["video_id"])
                        if not result or not result.get("success"):
                            logger.warning(f"⚠️ Skipping undownloadable track: {song['title']}")
                            continue
                        path = result["data"]["filepath"]
                        song["filepath"] = await local_cache.save(song["video_id"], path)
                except Exception as e:
                    logger.error(f"Lazy download failed for {song['title']}: {e}")
                    continue

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

                start_monitor(chat_id, song["filepath"])
                start_prefetch(chat_id)

                logger.info(f"✅ VC AUTO-PLAYING NEXT: {song['title']} in {chat_id}")
                return

            except Exception as e:
                logger.error(f"play_next error while playing '{song['title']}': {e}")
                continue

        logger.info(f"📭 Queue empty for chat {chat_id}, leaving call")
        cancel_prefetch(chat_id)
        active_chats.discard(chat_id)
        paused_chats.discard(chat_id)
        now_playing_song.pop(chat_id, None)
        try:
            await assistant_client.call_py.leave_call(chat_id)
        except Exception:
            pass


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
            "**◈ MISSING TRACK NAME ◈**\n\n"
            ">Tell me what to play.\n"
            ">Example: `/vplay Alan Walker Faded`"
        )
        return

    query = parts[1].strip()
    chat_id = message.chat.id
    requester = user_mention(message)

    status_msg = await message.reply(
        "**◈ SEARCHING ◈**\n\n"
        ">🔎 Finding your track…"
    )

    try:
        song = await get_song_ready(query, client.db)
        if not song:
            await status_msg.edit_text(
                "**◈ NOT FOUND ◈**\n\n"
                ">Couldn't find or download that track."
            )
            return

        active_calls = await assistant_client.call_py.calls
        is_actually_active = chat_id in active_calls

        if is_actually_active:
            queues[chat_id].append(song)
            await status_msg.edit_text(
                f"**◈ ADDED TO QUEUE ◈**\n\n"
                f">🎵 **{song['title']}**\n"
                f">📍 Position `#{len(queues[chat_id])}`\n"
                f">👤 Added by {requester}"
            )
            start_prefetch(chat_id)
            return

        active_chats.discard(chat_id)

        await status_msg.edit_text(
            "**◈ CONNECTING ◈**\n\n"
            ">📞 Joining voice chat…"
        )

        joined = await ensure_assistant_in_chat(client, chat_id)
        if not joined:
            await status_msg.edit_text(
                "**◈ ACCESS DENIED ◈**\n\n"
                ">Couldn't add the assistant to this group.\n"
                ">Make sure the bot is an **admin** with\n"
                ">permission to invite users."
            )
            return

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

        start_monitor(chat_id, song["filepath"])
        start_prefetch(chat_id)

        logger.info(f"✅ VC PLAYING: {song['title']} in chat {chat_id}")

    except Exception as e:
        logger.error(f"voice_play error: {e}")
        await status_msg.edit_text(f"**◈ ERROR ◈**\n\n>`{e}`")


@Bot.on_message(filters.command(["favshuffle", "shuffle"]) & filters.group)
async def voice_shuffle(client: Bot, message: Message):
    if not assistant_client or not assistant_client.call_py:
        await message.reply("🚫 **Voice chat engine isn't ready yet.**")
        return

    chat_id = message.chat.id
    requester = user_mention(message)

    favorites = FavoritesManager(client.db)
    fav_songs = await favorites.list_favorites(message.from_user.id, limit=50)

    if not fav_songs:
        await message.reply(
            "**◈ YOUR VAULT IS EMPTY ◈**\n\n"
            ">You haven't saved any tracks yet.\n"
            ">Tap ❤️ on any playing song to start\n"
            ">building your personal collection.\n\n"
            "__Then come back and let the shuffle work its magic ✨__"
        )
        return

    status_msg = await message.reply(
        f"**◈ SHUFFLE MODE ◈**\n\n"
        f">🔀 Loading `{len(fav_songs)}` tracks from your vault\n"
        f">⏳ Preparing the first track…"
    )

    try:
        shuffled = fav_songs.copy()
        random.shuffle(shuffled)

        local_cache = LocalCacheManager(client.db)
        engine = SearchEngine()

        first = shuffled.pop(0)
        first_video_id = first["video_id"]

        cached_path = await local_cache.get(first_video_id)
        if cached_path:
            first_path = cached_path
        else:
            result = await engine.download_song(first_video_id)
            if not result or not result.get("success"):
                await status_msg.edit_text(
                    "**◈ DOWNLOAD FAILED ◈**\n\n"
                    ">Couldn't prepare the first track."
                )
                return
            first_path = result["data"]["filepath"]
            first_path = await local_cache.save(first_video_id, first_path)

        first_song = {
            "video_id": first_video_id,
            "title": first["title"],
            "duration": 0,
            "uploader": first.get("uploader", "Unknown"),
            "filepath": first_path,
            "thumbnail": f"https://i.ytimg.com/vi/{first_video_id}/maxresdefault.jpg"
        }

        for fav in shuffled:
            queues[chat_id].append({
                "video_id": fav["video_id"],
                "title": fav["title"],
                "duration": 0,
                "uploader": fav.get("uploader", "Unknown"),
                "filepath": None,
                "thumbnail": f"https://i.ytimg.com/vi/{fav['video_id']}/maxresdefault.jpg"
            })

        active_calls = await assistant_client.call_py.calls
        is_actually_active = chat_id in active_calls

        if is_actually_active:
            queues[chat_id].insert(0, first_song)
            await status_msg.edit_text(
                f"**◈ SHUFFLE QUEUED ◈**\n\n"
                f">🔀 Added `{len(fav_songs)}` shuffled tracks\n"
                f">📋 Queue size `{len(queues[chat_id])}`"
            )
            start_prefetch(chat_id)
            return

        active_chats.discard(chat_id)
        await status_msg.edit_text(
            "**◈ CONNECTING ◈**\n\n"
            ">📞 Joining voice chat…"
        )

        joined = await ensure_assistant_in_chat(client, chat_id)
        if not joined:
            await status_msg.edit_text(
                "**◈ ACCESS DENIED ◈**\n\n"
                ">Couldn't add the assistant to this group.\n"
                ">Make sure the bot is an **admin** with\n"
                ">permission to invite users."
            )
            return

        await assistant_client.call_py.play(
            chat_id,
            MediaStream(
                first_song["filepath"],
                audio_parameters=AudioQuality.STUDIO
            )
        )

        active_chats.add(chat_id)
        started_by = f"{requester} 🔀"
        last_action_user.setdefault(chat_id, {})["play"] = started_by
        await status_msg.delete()

        await send_now_playing_card(client, chat_id, first_song, started_by)

        start_monitor(chat_id, first_song["filepath"])
        start_prefetch(chat_id)

        logger.info(f"✅ SHUFFLE PLAYING: {first_song['title']} + {len(shuffled)} queued in chat {chat_id}")

    except Exception as e:
        logger.error(f"voice_shuffle error: {e}")
        await status_msg.edit_text(f"**◈ ERROR ◈**\n\n>`{e}`")


@Bot.on_callback_query(filters.regex(r"^vc_pause$"))
async def cb_pause(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id

    if not await is_admin(client, chat_id, callback.from_user.id):
        await callback.answer("🔒 Only admins can control playback.", show_alert=True)
        return

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

    if not await is_admin(client, chat_id, callback.from_user.id):
        await callback.answer("🔒 Only admins can control playback.", show_alert=True)
        return

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

    if not await is_admin(client, chat_id, callback.from_user.id):
        await callback.answer("🔒 Only admins can control playback.", show_alert=True)
        return

    skipper = user_mention(callback)
    await callback.answer("⏭️ Skipping...")

    if not queues[chat_id]:
        await callback.message.reply(
            f"**◈ QUEUE EMPTY ◈**\n\n"
            f">Nothing left to skip to.\n"
            f">Stopped by {skipper}"
        )
        cancel_monitor(chat_id)
        cancel_prefetch(chat_id)
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

    last_action_user.setdefault(chat_id, {})["play"] = f"{skipper} ⏭"
    await play_next(chat_id)


@Bot.on_callback_query(filters.regex(r"^vc_stop$"))
async def cb_stop(client: Bot, callback: CallbackQuery):
    chat_id = callback.message.chat.id

    if not await is_admin(client, chat_id, callback.from_user.id):
        await callback.answer("🔒 Only admins can control playback.", show_alert=True)
        return

    stopper = user_mention(callback)
    queues[chat_id].clear()
    active_chats.discard(chat_id)
    paused_chats.discard(chat_id)
    now_playing_song.pop(chat_id, None)
    cancel_monitor(chat_id)
    cancel_prefetch(chat_id)

    try:
        await assistant_client.call_py.leave_call(chat_id)
        await callback.answer("⏹️ Stopped")
        try:
            await callback.message.edit_caption(
                (callback.message.caption or "") + f"\n\n>⏹️ Stopped by {stopper}",
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
        f"{i}. {song['title'][:35]}" for i, song in enumerate(queues[chat_id][:10], start=1)
    )
    if len(queues[chat_id]) > 10:
        text += f"\n\n...and {len(queues[chat_id]) - 10} more"

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
        video_id = song["video_id"]

        already_fav = await favorites.is_favorite(user_id, video_id)

        if already_fav:
            await favorites.remove(user_id, video_id)
            await callback.answer(
                f"💔 Removed '{song['title'][:30]}' from your favorites",
                show_alert=True
            )
        else:
            await favorites.add(
                user_id=user_id,
                video_id=video_id,
                title=song["title"],
                file_id="",
                uploader=song.get("uploader", "")
            )
            await callback.answer(
                f"❤️ Added '{song['title'][:30]}' to your favorites!",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"cb_fav error: {e}")
        await callback.answer(f"❌ {e}", show_alert=True)


@Bot.on_message(filters.command("vskip") & filters.group)
async def voice_skip(client: Bot, message: Message):
    chat_id = message.chat.id

    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply("🔒 **Only admins can control playback.**")
        return

    if not queues[chat_id]:
        await message.reply(
            "**◈ QUEUE EMPTY ◈**\n\n"
            ">Nothing left to skip to."
        )
        cancel_monitor(chat_id)
        cancel_prefetch(chat_id)
        try:
            await assistant_client.call_py.leave_call(chat_id)
            active_chats.discard(chat_id)
            paused_chats.discard(chat_id)
            now_playing_song.pop(chat_id, None)
        except Exception:
            pass
        return

    await message.reply("**◈ SKIPPING ◈**\n\n>⏭️ Loading next track…")
    await play_next(chat_id)


@Bot.on_message(filters.command("vstop") & filters.group)
async def voice_stop(client: Bot, message: Message):
    chat_id = message.chat.id

    if not await is_admin(client, chat_id, message.from_user.id):
        await message.reply("🔒 **Only admins can control playback.**")
        return

    queues[chat_id].clear()
    active_chats.discard(chat_id)
    paused_chats.discard(chat_id)
    now_playing_song.pop(chat_id, None)
    cancel_monitor(chat_id)
    cancel_prefetch(chat_id)

    try:
        await assistant_client.call_py.leave_call(chat_id)
        await message.reply(
            f"**◈ SESSION ENDED ◈**\n\n"
            f">⏹️ Left the voice chat\n"
            f">🗑 Queue cleared by {user_mention(message)}"
        )
        now_playing_msg.pop(chat_id, None)
    except Exception as e:
        await message.reply(f"**◈ ERROR ◈**\n\n>`{e}`")


@Bot.on_message(filters.command("vqueue") & filters.group)
async def voice_queue(client: Bot, message: Message):
    chat_id = message.chat.id

    if not queues[chat_id]:
        await message.reply(
            "**◈ QUEUE EMPTY ◈**\n\n"
            ">Nothing lined up right now."
        )
        return

    text = "**◈ CURRENT QUEUE ◈**\n\n"
    for i, song in enumerate(queues[chat_id][:20], start=1):
        text += f">`{i}.` 🎵 {song['title'][:50]}\n"

    if len(queues[chat_id]) > 20:
        text += f"\n__…and {len(queues[chat_id]) - 20} more tracks__"

    await message.reply(text)