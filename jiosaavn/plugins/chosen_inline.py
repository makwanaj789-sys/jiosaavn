from pyrogram.types import ChosenInlineResult

from jiosaavn.bot import Bot
from api.search_engine import SearchEngine


@Bot.on_chosen_inline_result()
async def chosen_inline(client: Bot, chosen: ChosenInlineResult):
    try:
        print("INLINE CLICK:", chosen.result_id)

        engine = SearchEngine()

        result = await engine.download_song(
            item_id=chosen.result_id
        )

        print(result)

        # Yaha next step me:
        # 1. MongoDB cache check
        # 2. Agar file_id hai -> send_audio(file_id)
        # 3. Nahi hai -> upload -> file_id save

    except Exception as e:
        print(e)