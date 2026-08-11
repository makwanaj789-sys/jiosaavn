import logging
from collections import defaultdict
from pyrogram import filters
from pyrogram.types import Message
from pytgcalls.types import MediaStream, Update
from pytgcalls.types.stream import StreamEnded

from jiosaavn.bot import Bot
from jiosaavn.assistant import Assistant
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

assistant_client: Assistant = None

# Queue system: each chat has its own list of pending songs
# format: {chat_id: [{"video_id": ..., "title": ..., "filepath": ...}, ...]}
queues = defaultdict(list)

# Tracks which chats currently have an active stream
active_chats = set()


def set_assistant(app: Assistant):
    global assistant_client
    assistant_client = app

    @app.call_py.on_update(filters.stream_end)
    async def on_stream_end(client, update: Update):
        if isinstance(update, StreamEnded):
            chat_id = update.chat_id
            await play_next(chat_id)


async def download_and_get_info(query: str):
    engine = SearchEngine()
    response = await engine.search(query)
    results = response.get("results", [])

    if not results:
        return None

    video_id = results[0]["id"]
    title = results[0].get("title", "Unknown")

    result = await engine.download_song(video_id)
    if not result or not result.get("success"):
        return None

    filepath = result["data"]["filepath"]

    return {"video_id": video_id, "title": title, "filepath": filepath}


async def play_next(chat_id: int):
    if not queues[chat_id]:
        active_chats.discard(chat_id)
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
        song = await download_and_get_info(query)
        if not song:
            await status_msg.edit_text("❌ **Couldn't find or download that song.**")
            return

        if chat_id in active_chats:
            queues[chat_id].append(song)
            await status_msg.edit_text(
                f"➕ **Added to Queue!**\n\n"
                f"🎵 **Track:** {song['title']}\n"
                f"📍 **Position:** #{len(queues[chat_id])}"
            )
            return

        await status_msg.edit_text("📞 **Joining voice chat...**")

        try:
            await assistant_client.call_py.play(
                chat_id,
                MediaStream(song["filepath"])
            )
        except Exception:
            await assistant_client.call_py.change_stream(
                chat_id,
                MediaStream(song["filepath"])
            )

        active_chats.add(chat_id)
        await status_msg.edit_text(f"🎶 **Now Playing**\n\n🎧 {song['title']}")
        logger.info(f"✅ VC PLAYING: {song['title']} in chat {chat_id}")

    except Exception as e:
        logger.error(f"voice_play error: {e}")
        await status_msg.edit_text(f"❌ **Error:** `{e}`")


@Bot.on_message(filters.command("vpause") & filters.group)
async def voice_pause(client: Bot, message: Message):
    try:
        await assistant_client.call_py.pause(message.chat.id)
        await message.reply("⏸️ **Paused.**")
    except Exception as e:
        await message.reply(f"❌ **Error:** `{e}`")


@Bot.on_message(filters.command("vresume") & filters.group)
async def voice_resume(client: Bot, message: Message):
    try:
        await assistant_client.call_py.resume(message.chat.id)
        await message.reply("▶️ **Resumed.**")
    except Exception as e:
        await message.reply(f"❌ **Error:** `{e}`")


@Bot.on_message(filters.command("vskip") & filters.group)
async def voice_skip(client: Bot, message: Message):
    chat_id = message.chat.id

    if not queues[chat_id]:
        await message.reply("📭 **Queue is empty, nothing to skip to.**")
        try:
            await assistant_client.call_py.leave_call(chat_id)
            active_chats.discard(chat_id)
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

    try:
        await assistant_client.call_py.leave_call(chat_id)
        await message.reply("⏹️ **Left the voice chat.** Queue cleared.")
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