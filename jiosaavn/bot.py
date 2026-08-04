from .database import Database
from .config.settings import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    DATABASE_URL,
    BOT_COMMANDS
)
from .app_webpage import start_web, stop_web
from pyrogram.handlers import RawUpdateHandler

from pyrogram import Client
from pyrogram.types import BotCommand, BotCommandScopeAllPrivateChats

import logging

logger = logging.getLogger(__name__)

STORAGE_CHAT_ID = -1004333026215

class Bot(Client):

    def __init__(self):
        super().__init__(
            name="jiosaavn",
            bot_token=BOT_TOKEN,
            api_id=int(API_ID),
            api_hash=API_HASH,
            sleep_threshold=30,
            max_concurrent_transmissions=10,
            plugins={
                "root": "jiosaavn.plugins"
            }
        )

        self.db = Database(DATABASE_URL)
        self.web_runner = None

    async def start(self):
        await super().start()

        self.web_runner = await start_web()

        print(f"Bot started: @{self.me.username}", flush=True)

        await self.add_commands()

        try:
            chat = await self.get_chat(STORAGE_CHAT_ID)
            logger.info(f"✅ Storage channel resolved: {chat.title}")
        except Exception as e:
            logger.error(f"❌ Could not resolve storage channel {STORAGE_CHAT_ID}: {e}")

        # 🔬 Temporary debug: raw update inspect karo
        async def raw_debug_handler(client, update, users, chats):
            update_name = type(update).__name__
            if "InlineSend" in update_name or "ChosenInline" in update_name:
                logger.info(f"🔬 RAW UPDATE: {update_name}")
                logger.info(f"🔬 RAW DATA: {update}")

        self.add_handler(RawUpdateHandler(raw_debug_handler))
        logger.info("🔬 Raw debug handler registered")

        return self

    async def stop(self, *args, **kwargs):

        if self.web_runner:
            await stop_web(self.web_runner)

        await super().stop(*args, **kwargs)

    async def add_commands(self):

        commands = [
            BotCommand(
                command.strip(),
                description.strip()
            )
            for command, description in BOT_COMMANDS
        ]

        await self.set_bot_commands(
            commands=commands,
            scope=BotCommandScopeAllPrivateChats()
        )