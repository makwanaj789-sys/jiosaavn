from pyrogram.types import ChosenInlineResult, InputMediaAudio
from jiosaavn.bot import Bot
from api.inline_helper import InlineHelper

@Bot.on_chosen_inline_result()
async def on_chosen(client, result: ChosenInlineResult):
    result_id = result.result_id

    if not result_id.startswith("dl_"):
        return  # ye already cached audio tha, Telegram ne khud bhej diya

    video_id = result_id.replace("dl_", "")
    inline_message_id = result.inline_message_id

    if not inline_message_id:
        return

    helper = InlineHelper(client)
    song = await helper.get_or_create(video_id)

    if not song:
        await client.edit_inline_message_text(
            inline_message_id,
            "❌ Download failed."
        )
        return

    await client.edit_inline_message_media(
        inline_message_id,
        InputMediaAudio(
            media=song["file_id"],
            caption=f"🎵 {song['title']}"
        )
    )