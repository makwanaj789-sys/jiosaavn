import logging
from pyrogram import Client
from pytgcalls import PyTgCalls

from jiosaavn.config.settings import API_ID, API_HASH, ASSISTANT_SESSION

logger = logging.getLogger(__name__)


class Assistant(Client):
    def __init__(self):
        super().__init__(
            name="assistant",
            api_id=int(API_ID),
            api_hash=API_HASH,
            session_string=ASSISTANT_SESSION,
            in_memory=True
        )
        self.call_py: PyTgCalls | None = None

    async def start(self, *args, **kwargs):
        await super().start()
        me = await self.get_me()
        print(f"Assistant started: @{me.username or me.first_name}", flush=True)

        self.call_py = PyTgCalls(self)
        await self.call_py.start()
        print("PyTgCalls started ✅", flush=True)

        return self

    async def stop(self, *args, **kwargs):
        if self.call_py:
            await self.call_py.stop()
        await super().stop(*args, **kwargs)