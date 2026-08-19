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

    # 🔥 Background cache warmer (default OFF — toggle with /warmer)
    warmer_task = None
    try:
        warmer_module = importlib.import_module("jiosaavn.plugins.cache_warmer")
        warmer_task = warmer_module.start_warmer(bot)
        print("✅ Cache warmer loop registered", flush=True)
    except Exception as e:
        logging.getLogger(__name__).error(f"Cache warmer failed to start: {e}")

    print("✅ Bot and Assistant both started!", flush=True)

    await idle()

    if warmer_task and not warmer_task.done():
        warmer_task.cancel()

    await bot.stop()
    await assistant.stop()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()