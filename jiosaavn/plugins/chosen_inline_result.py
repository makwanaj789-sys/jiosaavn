import logging
import traceback

from pyrogram.types import ChosenInlineResult, InputMediaAudio
from jiosaavn.bot import Bot
from api.inline_helper import InlineHelper

logger = logging.getLogger(__name__)


@Bot.on_chosen_inline_result()
async def on_chosen(client, result: ChosenInlineResult):
    result_id = result.result_id
    logger.info(f"🎯 CHOSEN INLINE RESULT: {result_id}")
    logger.info(result)
    logger.info(result.__dict__)

    if not result_id.startswith("dl_"):
        return

    video_id = result_id.replace("dl_", "")
    inline_message_id = result.inline_message_id
    logger.info(f"📩 inline_message_id: {inline_message_id}")

    if not inline_message_id:
        logger.warning("❌ No inline_message_id received — cannot edit message.")
        return

    try:
        helper = InlineHelper(client)
        song = await helper.get_or_create(video_id)

        if not song:
            await client.edit_inline_text(inline_message_id, "❌ Download failed.")
            return

        await client.edit_inline_media(
            inline_message_id,
            InputMediaAudio(media=song["file_id"], caption=f"🎵 {song['title']}")
        )

        logger.info(f"✅ INLINE MESSAGE EDITED SUCCESSFULLY: {song['title']}")

    except Exception as e:
        logger.error(f"❌ CHOSEN_INLINE_RESULT ERROR: {e}")
        logger.error(traceback.format_exc())
        try:
            await client.edit_inline_text(inline_message_id, f"❌ Error: `{type(e).__name__}: {e}`")
        except Exception as e2:
            logger.error(f"❌ Even edit_text failed: {e2}")