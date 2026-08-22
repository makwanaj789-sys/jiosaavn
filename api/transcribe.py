import os
import logging
import aiohttp

from jiosaavn.config.settings import GROQ_API_KEY

logger = logging.getLogger(__name__)

TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
TRANSCRIBE_MODEL = "whisper-large-v3-turbo"

CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
CHAT_MODEL = "llama-3.3-70b-versatile"


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
        data.add_field("model", TRANSCRIBE_MODEL)
        data.add_field("temperature", "0")
        data.add_field(
            "file",
            open(filepath, "rb"),
            filename=os.path.basename(filepath),
            content_type="audio/ogg"
        )

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

        async with aiohttp.ClientSession() as session:
            async with session.post(TRANSCRIBE_URL, headers=headers, data=data, timeout=60) as resp:
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


async def refine_query(raw: str) -> str:
    """
    Turns a rough transcription into a clean song search query.
    Falls back to the original text if anything goes wrong.
    """
    if not GROQ_API_KEY or not raw:
        return raw

    system = (
        "You convert speech transcriptions into YouTube music search queries. "
        "The speaker is naming a song, artist, or film — often in Hindi, Punjabi, "
        "or Hinglish, and the transcription may be misheard or in Devanagari.\n\n"
        "Rules:\n"
        "- Always reply in Roman script, never Devanagari\n"
        "- Correct obvious mishearings to the real song title\n"
        "- Add the film or artist name if you recognise the song\n"
        "- Drop filler words like 'play', 'bajao', 'gaana', 'sunao'\n"
        "- Reply with ONLY the search query, nothing else\n"
        "- If you cannot identify anything, reply with the input transliterated"
    )

    try:
        payload = {
            "model": CHAT_MODEL,
            "temperature": 0.2,
            "max_tokens": 60,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": raw},
            ],
        }

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(CHAT_URL, headers=headers, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"REFINE: HTTP {resp.status} — {body[:200]}")
                    return raw

                result = await resp.json()
                cleaned = result["choices"][0]["message"]["content"].strip()
                cleaned = cleaned.strip('"').strip("'")

                if not cleaned or len(cleaned) > 120:
                    return raw

                logger.info(f"✨ REFINED: '{raw}' → '{cleaned}'")
                return cleaned

    except Exception as e:
        logger.warning(f"REFINE error: {e}")
        return raw