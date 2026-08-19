import os
import asyncio
import random
import logging

import yt_dlp

from pyrogram import filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from jiosaavn.bot import Bot
from jiosaavn.emojis import *
from jiosaavn.config.settings import OWNER_ID
from api.search_engine import SearchEngine
from api.inline_helper import InlineHelper
from api.cache import CacheManager

logger = logging.getLogger(__name__)

# ---- pacing (deliberately slow: datacenter IPs get flagged for bursts) ----
MIN_GAP = 240        # 4 min between downloads
MAX_GAP = 420        # up to 7 min
MAX_PER_RUN = 12     # new tracks per cycle
CYCLE_REST = 3600    # 1 hr between cycles

COOKIES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "cookies.txt"
)

# YouTube pages that list what's popular right now
DISCOVERY_URLS = [
    "https://www.youtube.com/feed/trending?bp=4gINGgt5dG1hX2NoYXJ0cw%3D%3D",  # music tab
    "https://www.youtube.com/feed/trending",
]

_warmer_task = None


# =====================================================================
# ON / OFF STATE (stored globally under chat_id 0)
# =====================================================================

async def is_enabled(db) -> bool:
    try:
        doc = await db.chat_settings.find_one({"chat_id": 0})
        return bool(doc and doc.get("warmer_enabled", False))
    except Exception:
        return False


async def set_enabled(db, value: bool):
    await db.chat_settings.update_one(
        {"chat_id": 0},
        {"$set": {"chat_id": 0, "warmer_enabled": value}},
        upsert=True
    )


# =====================================================================
# DISCOVERY — find popular tracks without any hardcoded list
# =====================================================================

def _flat_extract(url: str, limit: int = 40):
    """Blocking yt-dlp call — metadata only, no downloading."""
    opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "playlistend": limit,
        "extractor_args": {"youtube": {"player_client": ["web_safari", "web", "mweb"]}},
    }
    if os.path.exists(COOKIES):
        opts["cookiefile"] = COOKIES

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    out = []
    for e in (info or {}).get("entries", []) or []:
        vid = e.get("id")
        if vid:
            out.append({
                "video_id": vid,
                "title": e.get("title", "Unknown"),
                "uploader": e.get("uploader") or e.get("channel") or "Unknown",
            })
    return out


async def discover_trending():
    """Whatever YouTube is currently pushing as popular."""
    found = []
    for url in DISCOVERY_URLS:
        try:
            items = await asyncio.to_thread(_flat_extract, url, 40)
            if items:
                logger.info(f"🔥 WARMER: discovered {len(items)} from trending")
                found.extend(items)
                break
        except Exception as e:
            logger.warning(f"WARMER: discovery failed for {url}: {e}")
    return found


async def discover_from_artists(db):
    """
    Grows organically: takes artists already in the cache and looks up
    more of their music. No manual list needed.
    """
    try:
        artists = await db.music_cache.distinct("uploader")
    except Exception as e:
        logger.warning(f"WARMER: artist lookup failed: {e}")
        return []

    artists = [a for a in artists if a and a.lower() != "unknown"]
    if not artists:
        return []

    random.shuffle(artists)
    picks = artists[:6]

    found = []
    engine = SearchEngine()
    for artist in picks:
        try:
            clean = artist.replace(" - Topic", "").strip()
            resp = await engine.search(f"{clean} songs")
            for r in (resp.get("results") or [])[:5]:
                if r.get("id"):
                    found.append({
                        "video_id": r["id"],
                        "title": r.get("title", "Unknown"),
                        "uploader": r.get("uploader", clean),
                    })
        except Exception as e:
            logger.warning(f"WARMER: artist search '{artist}' failed: {e}")
        await asyncio.sleep(5)

    return found


async def discover_from_user_searches(db):
    """What this bot's own users actually look for — highest value."""
    try:
        top = await db.top_queries(limit=25)
    except Exception:
        return []

    found = []
    engine = SearchEngine()
    for doc in top:
        q = doc.get("_id")
        if not q:
            continue
        try:
            resp = await engine.search(q)
            results = resp.get("results") or []
            if results and results[0].get("id"):
                found.append({
                    "video_id": results[0]["id"],
                    "title": results[0].get("title", "Unknown"),
                    "uploader": results[0].get("uploader", "Unknown"),
                })
        except Exception:
            pass
        await asyncio.sleep(5)

    return found


# =====================================================================
# WARMING
# =====================================================================

def voice_chat_busy() -> bool:
    try:
        from jiosaavn.plugins import voice_chat
        return bool(voice_chat.active_chats)
    except Exception:
        return False


async def warmer_loop(client: Bot):
    await asyncio.sleep(120)
    logger.info("🔥 WARMER: loop started")

    while True:
        try:
            if not await is_enabled(client.db):
                await asyncio.sleep(300)
                continue

            cache = CacheManager(client.db)
            helper = InlineHelper(client)

            candidates = []
            candidates += await discover_from_user_searches(client.db)
            candidates += await discover_trending()
            candidates += await discover_from_artists(client.db)

            # dedupe by video_id
            seen, unique = set(), []
            for c in candidates:
                if c["video_id"] not in seen:
                    seen.add(c["video_id"])
                    unique.append(c)

            random.shuffle(unique)

            if not unique:
                logger.info("🔥 WARMER: nothing discovered, resting")
                await asyncio.sleep(CYCLE_REST)
                continue

            logger.info(f"🔥 WARMER: {len(unique)} candidates this cycle")
            done = 0

            for item in unique:
                if done >= MAX_PER_RUN:
                    break

                if not await is_enabled(client.db):
                    logger.info("🔥 WARMER: switched off mid-cycle")
                    break

                if voice_chat_busy():
                    logger.info("🔥 WARMER: voice chat live, pausing")
                    await asyncio.sleep(300)
                    continue

                vid = item["video_id"]

                try:
                    if await cache.get(vid):
                        continue

                    song = await helper.get_or_create(vid)
                    if song:
                        done += 1
                        logger.info(f"✅ WARMER: cached '{song['title']}'")
                    else:
                        logger.warning(f"⚠️ WARMER: failed '{item['title']}'")

                except Exception as e:
                    logger.warning(f"WARMER: error on '{item['title']}': {e}")

                await asyncio.sleep(random.randint(MIN_GAP, MAX_GAP))

            logger.info(f"🔥 WARMER: cycle finished — {done} new tracks")
            await asyncio.sleep(CYCLE_REST)

        except asyncio.CancelledError:
            logger.info("🔥 WARMER: cancelled")
            return
        except Exception as e:
            logger.error(f"WARMER loop error: {e}")
            await asyncio.sleep(600)


def start_warmer(client: Bot):
    global _warmer_task
    _warmer_task = asyncio.create_task(warmer_loop(client))
    return _warmer_task


# =====================================================================
# OWNER CONTROLS
# =====================================================================

def warmer_markup(enabled: bool):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{'✦ ' if enabled else ''}ᴏɴ",
                callback_data="warmer_on",
                style=enums.ButtonStyle.SUCCESS if enabled else enums.ButtonStyle.DEFAULT
            ),
            InlineKeyboardButton(
                f"{'✦ ' if not enabled else ''}ᴏꜰꜰ",
                callback_data="warmer_off",
                style=enums.ButtonStyle.DANGER if not enabled else enums.ButtonStyle.DEFAULT
            ),
        ],
        [
            InlineKeyboardButton(
                "ʀᴇꜰʀᴇꜱʜ",
                callback_data="warmer_status",
                style=enums.ButtonStyle.PRIMARY
            )
        ]
    ])


async def warmer_text(client: Bot) -> str:
    enabled = await is_enabled(client.db)
    try:
        total = await client.db.music_cache.count_documents({})
    except Exception:
        total = 0

    state = f"{E_CHECK} **ᴏɴ**" if enabled else f"{E_STOP} **ᴏꜰꜰ**"

    return (
        f"**◈ ᴄᴀᴄʜᴇ ᴡᴀʀᴍᴇʀ ◈**\n\n"
        f">{E_SETTINGS} Status {state}\n"
        f">{E_CASSETTE} Cached tracks `{total}`\n"
        f">{E_DOWNLOAD} Up to `{MAX_PER_RUN}` per cycle\n"
        f">{E_SHUFFLE} Gap `{MIN_GAP//60}–{MAX_GAP//60}` min · rest `{CYCLE_REST//60}` min\n\n"
        f"__{E_SPARKLE} Finds popular tracks on its own and caches them__"
    )


@Bot.on_message(filters.command("warmer"))
async def warmer_panel(client: Bot, message: Message):
    logger.info(f"🔥 WARMER CMD from {message.from_user.id if message.from_user else '?'}")

    if not message.from_user or message.from_user.id != int(OWNER_ID):
        await message.reply("🔒 Owner only.")
        return

    enabled = await is_enabled(client.db)
    await message.reply(await warmer_text(client), reply_markup=warmer_markup(enabled))


@Bot.on_callback_query(filters.regex(r"^warmer_(on|off|status)$"))
async def warmer_toggle(client: Bot, callback: CallbackQuery):
    if callback.from_user.id != int(OWNER_ID):
        await callback.answer("🔒 Owner only.", show_alert=True)
        return

    action = callback.data.replace("warmer_", "")

    if action == "on":
        await set_enabled(client.db, True)
        await callback.answer("🔥 Warmer switched on")
    elif action == "off":
        await set_enabled(client.db, False)
        await callback.answer("⏹️ Warmer switched off")
    else:
        await callback.answer()

    enabled = await is_enabled(client.db)
    try:
        await callback.message.edit_text(
            await warmer_text(client),
            reply_markup=warmer_markup(enabled)
        )
    except Exception:
        pass