import logging
from pyrogram import RawUpdateHandler
from jiosaavn.bot import Bot

logger = logging.getLogger(__name__)


async def raw_handler(client, update, users, chats):
    update_name = type(update).__name__
    if "InlineSend" in update_name or "ChosenInline" in update_name:
        logger.info(f"🔬 RAW UPDATE: {update_name}")
        logger.info(f"🔬 RAW DATA: {update}")


Bot.add_handler(RawUpdateHandler(raw_handler))