import logging
import logging.config
import importlib

from dotenv import load_dotenv


def main():

    try:
        logging.config.fileConfig("logging.conf")
    except Exception:
        logging.basicConfig(level=logging.INFO)

    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pyrogram").setLevel(logging.INFO)

    load_dotenv()

    bot_module = importlib.import_module("jiosaavn.bot")
    bot = bot_module.Bot()

    bot.run()


if __name__ == "__main__":
    main()