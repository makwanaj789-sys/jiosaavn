import asyncio
import logging
import logging.config
import importlib

from dotenv import load_dotenv
from pyrogram import idle


def setup_logging():
    try:
        logging.config.fileConfig("logging.conf")
    except Exception:
        logging.basicConfig(level=logging.INFO)

    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pyrogram").setLevel(logging.INFO)


async def run():
    load_dotenv()
    setup_logging()

    bot_module = importlib.import_module("jiosaavn.bot")
    assistant_module = importlib.import_module("jiosaavn.assistant")

    bot = bot_module.Bot()
    assistant = assistant_module.Assistant()

    await bot.start()
    await assistant.start()

    # 🔥 Voice chat plugin ko assistant reference do
    assistant.bot_ref = bot
    voice_chat_module = importlib.import_module("jiosaavn.plugins.voice_chat")
    voice_chat_module.set_assistant(assistant)

    print("✅ Bot and Assistant both started!", flush=True)

    await idle()

    await bot.stop()
    await assistant.stop()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()