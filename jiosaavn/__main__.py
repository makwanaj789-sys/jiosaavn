import logging
import logging.config
import importlib
from dotenv import load_dotenv

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass


def main():
    print("DEBUG 1: main started", flush=True)

    # Setup logging
    try:
        logging.config.fileConfig("logging.conf")
    except Exception:
        logging.basicConfig(level=logging.INFO)
        logging.warning("logging.conf not found - using basicConfig()")

    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)

    print("DEBUG 2: logging configured", flush=True)

    # Load environment variables
    load_dotenv()
    print("DEBUG 3: environment loaded", flush=True)

    # Import bot
    print("DEBUG 4: importing jiosaavn.bot", flush=True)
    bot_module = importlib.import_module("jiosaavn.bot")
    print("DEBUG 5: bot module imported", flush=True)

    # Initialize bot
    bot = bot_module.Bot()
    print("DEBUG 6: bot object created", flush=True)

    # Run Pyrogram bot
    print("DEBUG 7: starting bot.run()", flush=True)
    bot.run()

    print("DEBUG 8: bot stopped", flush=True)


if __name__ == "__main__":
    main()