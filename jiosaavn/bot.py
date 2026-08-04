from .database import Database
from .config.settings import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    DATABASE_URL,
    BOT_COMMANDS
)
from .app_webpage import start_web, stop_web

from pyrogram import Client
from pyrogram.types import BotCommand, BotCommandScopeAllPrivateChats

import logging

logger = logging.getLogger(__name__)

STORAGE_CHAT_ID = -1003713614798


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

        print(
            f"Bot started: @{self.me.username}",
            flush=True
        )

        await self.add_commands()

        # 🔥 Storage channel ko resolve karo taaki send_audio() peer error na de
        try:
            chat = await self.get_chat(STORAGE_CHAT_ID)
            logger.info(f"✅ Storage channel resolved: {chat.title}")
        except Exception as e:
            logger.error(f"❌ Could not resolve storage channel {STORAGE_CHAT_ID}: {e}")
            logger.error("👉 Check: bot us channel mein ADMIN hai ya nahi, aur ID sahi hai ya nahi")

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