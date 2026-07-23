import logging
import logging.config
import importlib
import asyncio
import signal
import threading
import aiohttp
from dotenv import load_dotenv

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

running = True  # Used to gracefully stop the loop








def main():
    # Setup logging
    try:
        logging.config.fileConfig('logging.conf')
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.warning("⚠️ logging.conf not found — using basicConfig()")

    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)

    # Load environment variables
    load_dotenv()

    # Import and initialize bot
    bot_module = importlib.import_module("jiosaavn.bot")
    bot = bot_module.Bot()

   

    # Run the bot (Pyrogram manages its own loop)
    bot.run()

    
    logging.info("✅ Bot stopped. Exiting...")


if __name__ == "__main__":
    main()
