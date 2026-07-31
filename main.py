import asyncio
from jiosaavn.bot import Bot

async def main():
    # Bot start karo
    print("🚀 Starting Bot...")
    await Bot.start()
    print("✅ Bot Started: @AartiMusic_bot")
    await asyncio.Event().wait()  # Bot ko chalta rakhne ke liye

if __name__ == "__main__":
    asyncio.run(main())