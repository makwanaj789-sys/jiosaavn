import logging
from pyrogram import filters
from pyrogram.types import Message
from pytgcalls.types import MediaStream

from jiosaavn.bot import Bot
from jiosaavn.assistant import Assistant
from api.search_engine import SearchEngine

logger = logging.getLogger(__name__)

# Global reference — bot.py mein hum assistant object ko yahan set karenge
assistant_client: Assistant = None


def set_assistant(app: Assistant):
    global assistant_client
    assistant_client = app


@Bot.on_message(filters.command("vplay") & filters.group)
async def voice_play(client: Bot, message: Message):
    if not assistant_client or not assistant_client.call_py:
        await message.reply("❌ Voice chat system abhi ready nahi hai.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Gaana naam do.\nExample: `/vplay Alan Walker Faded`")
        return

    query = parts[1].strip()
    chat_id = message.chat.id

    status_msg = await message.reply("🔎 𝘚𝘦𝘢𝘳𝘤𝘩𝘪𝘯𝘨 𝘢𝘯𝘥 𝘱𝘳𝘦𝘱𝘢𝘳𝘪𝘯𝘨...")

    try:
        engine = SearchEngine()
        response = await engine.search(query)

        results = response.get("results", [])
        if not results:
            await status_msg.edit_text("❌ Koi gaana nahi mila.")
            return

        video_id = results[0]["id"]
        title = results[0].get("title", "Unknown")

        await status_msg.edit_text(f"⬇️ 𝘋𝘰𝘸𝘯𝘭𝘰𝘢𝘥𝘪𝘯𝘨: `{title}`...")

        result = await engine.download_song(video_id)
        if not result or not result.get("success"):
            await status_msg.edit_text("❌ Download fail ho gaya.")
            return

        filepath = result["data"]["filepath"]

        await status_msg.edit_text(f"📞 𝘑𝘰𝘪𝘯𝘪𝘯𝘨 𝘷𝘰𝘪𝘤𝘦 𝘤𝘩𝘢𝘵...")

        try:
            await assistant_client.call_py.play(
                chat_id,
                MediaStream(filepath)
            )
        except Exception as e:
            # Agar already ek call chal rahi hai, to change_stream use karo
            try:
                await assistant_client.call_py.change_stream(
                    chat_id,
                    MediaStream(filepath)
                )
            except Exception as e2:
                logger.error(f"VC join/play error: {e2}")
                await status_msg.edit_text(f"❌ Voice chat join nahi hua.\n\n`{e2}`\n\nZaroor check karo VC already active hai group mein.")
                return

        await status_msg.edit_text(f"🎶 **Now Playing:** {title}")
        logger.info(f"✅ VC PLAYING: {title} in chat {chat_id}")

    except Exception as e:
        logger.error(f"voice_play error: {e}")
        await status_msg.edit_text(f"❌ Error: `{e}`")


@Bot.on_message(filters.command("vstop") & filters.group)
async def voice_stop(client: Bot, message: Message):
    if not assistant_client or not assistant_client.call_py:
        await message.reply("❌ Voice chat system abhi ready nahi hai.")
        return

    try:
        await assistant_client.call_py.leave_call(message.chat.id)
        await message.reply("⏹️ Voice chat se nikal gaya.")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")