from .database import Database
from .config.settings import API_ID, API_HASH, BOT_TOKEN, DATABASE_URL, BOT_COMMANDS
from .app_webpage import start_web, stop_web

from pyrogram import Client
from pyrogram.types import BotCommand, BotCommandScopeAllPrivateChats


class Bot(Client):

    def __init__(self):
        super().__init__(
            name="jiosaavn",
            bot_token=BOT_TOKEN,
            api_id=API_ID,
            api_hash=API_HASH,
            sleep_threshold=30,
            max_concurrent_transmissions=10,
            plugins={
                "root": "jiosaavn/plugins"
            }
        )
        self.db = Database(DATABASE_URL)

    async def start(self):
        print("BOT DEBUG 1: start() entered", flush=True)

        print("BOT DEBUG 2: connecting to Telegram...", flush=True)
        await super().start()

        print("BOT DEBUG 3: Telegram connected", flush=True)

        print("BOT DEBUG 4: starting web server...", flush=True)
        self.web_runner = await start_web()

        print("BOT DEBUG 5: web server started", flush=True)

        print(
            f"New session started for {self.me.first_name}({self.me.username})",
            flush=True
        )

        print("BOT DEBUG 6: adding commands...", flush=True)
        await self.add_commands()

        print("BOT DEBUG 7: startup completed", flush=True)

    async def stop(self):
        await super().stop()
        await stop_web(self.web_runner)
        print("Session stopped. Bye!!", flush=True)

    async def add_commands(self):
        commands = [
            BotCommand(command.strip(), description.strip())
            for command, description in BOT_COMMANDS
        ]

        await self.set_bot_commands(
            commands=commands,
            scope=BotCommandScopeAllPrivateChats()
        )