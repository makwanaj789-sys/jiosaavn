import os
import logging
import aiohttp

from jiosaavn.config.settings import GROQ_API_KEY

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = "whisper-large-v3-turbo"


async def transcribe(filepath: str) -> str | None:
    """
    Sends an audio file to Groq's Whisper endpoint and returns the text.
    Returns None if anything goes wrong.
    """
    if not GROQ_API_KEY:
        logger.error("TRANSCRIBE: GROQ_API_KEY is not set")
        return None

    if not os.path.exists(filepath):
        logger.error(f"TRANSCRIBE: file missing — {filepath}")
        return None

    try:
        data = aiohttp.FormData()
        data.add_field("model", MODEL)
        # A hint helps Whisper handle Hinglish song names far better
        data.add_field(
            "prompt",
            "The user is naming a song, artist, or movie. "
            "Names may be Hindi, Punjabi, or English."
        )
        data.add_field("temperature", "0")
        data.add_field(
            "file",
            open(filepath, "rb"),
            filename=os.path.basename(filepath),
            content_type="audio/ogg"
        )

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_URL, headers=headers, data=data, timeout=60) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(f"TRANSCRIBE: HTTP {resp.status} — {body[:200]}")
                    return None

                result = await resp.json()
                text = (result.get("text") or "").strip()

                logger.info(f"🎙 TRANSCRIBED: '{text}'")
                return text or None

    except Exception as e:
        logger.error(f"TRANSCRIBE error: {e}")
        return None