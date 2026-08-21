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
MIN_GAP = 180            # 3 min between downloads
MAX_GAP = 240            # up to 4 min
MAX_PER_RUN = 32         # new tracks per automatic cycle
CYCLE_REST = 1800        # 30 min between cycles
ARTIST_LIMIT = 15        # tracks pulled per artist
MAX_LINES = 500          # max songs in a multi-line /warm
RESULTS_PER_SONG = 3     # search results cached per song line

COOKIES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "cookies.txt"
)

DISCOVERY_URLS = [
    "https://www.youtube.com/feed/trending?bp=4gINGgt5dG1hX2NoYXJ0cw%3D%3D",
    "https://www.youtube.com/feed/trending",
]

_warmer_task = None

# on-demand queue (/warm) — always takes priority over automatic warming
manual_queue = []
manual_worker = None
manual_active = False

# stops manual + automatic warming from downloading at the same time
download_lock = asyncio.Lock()


def manual_busy() -> bool:
    """True while /warm still has work to do."""
    return manual_active or bool(manual_queue)


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
# VOICE CHAT CHECK
# =====================================================================

async def voice_chat_busy() -> bool:
    """
    Checks live calls rather than the local set — the set can go stale
    if a call ends unexpectedly.
    """
    try:
        from jiosaavn.plugins import voice_chat
        if not voice_chat.assistant_client or not voice_chat.assistant_client.call_py:
            return False
        calls = await voice_chat.assistant_client.call_py.calls
        return bool(calls)
    except Exception:
        return False


# =====================================================================
# AUTOMATIC WARMING
# =====================================================================

async def warmer_loop(client: Bot):
    await asyncio.sleep(120)
    logger.info("🔥 WARMER: loop started")

    while True:
        try:
            if not await is_enabled(client.db):
                await asyncio.sleep(300)
                continue

            # Manual /warm always wins — wait for it to finish
            if manual_busy():
                logger.info("🔥 WARMER: manual queue active, standing by")
                await asyncio.sleep(120)
                continue

            cache = CacheManager(client.db)
            helper = InlineHelper(client)

            candidates = []
            candidates += await discover_from_user_searches(client.db)
            candidates += await discover_trending()
            candidates += await discover_from_artists(client.db)

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

                # Yield mid-cycle too if /warm arrives
                if manual_busy():
                    logger.info("🔥 WARMER: manual queue started, pausing cycle")
                    break

                if await voice_chat_busy():
                    logger.info("🔥 WARMER: voice chat live, pausing")
                    await asyncio.sleep(300)
                    continue

                vid = item["video_id"]

                try:
                    if await cache.get(vid):
                        continue

                    async with download_lock:
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
# ON-DEMAND WARMING (/warm)
# =====================================================================

async def manual_loop(client: Bot):
    """Drains the on-demand queue with the same careful pacing."""
    global manual_active

    manual_active = True
    logger.info("🎯 MANUAL: worker started")

    try:
        while manual_queue:
            item = manual_queue.pop(0)

            if await voice_chat_busy():
                manual_queue.insert(0, item)
                logger.info("🎯 MANUAL: voice chat live, pausing")
                await asyncio.sleep(300)
                continue

            try:
                cache = CacheManager(client.db)
                if await cache.get(item["video_id"]):
                    continue

                async with download_lock:
                    helper = InlineHelper(client)
                    song = await helper.get_or_create(item["video_id"])

                if song:
                    logger.info(
                        f"✅ MANUAL: cached '{song['title']}' "
                        f"({len(manual_queue)} left)"
                    )
                else:
                    logger.warning(f"⚠️ MANUAL: failed '{item['title']}'")

            except Exception as e:
                logger.warning(f"MANUAL: error on '{item['title']}': {e}")

            if manual_queue:
                await asyncio.sleep(random.randint(MIN_GAP, MAX_GAP))

        logger.info("🎯 MANUAL: queue drained — automatic warmer may resume")

    except asyncio.CancelledError:
        logger.info("🎯 MANUAL: cancelled")
    finally:
        manual_active = False


def ensure_manual_worker(client: Bot):
    global manual_worker
    if manual_worker is None or manual_worker.done():
        manual_worker = asyncio.create_task(manual_loop(client))


def already_queued(video_id: str) -> bool:
    return any(q["video_id"] == video_id for q in manual_queue)


@Bot.on_message(filters.command("warm") & filters.user(int(OWNER_ID)))
async def warm_artist(client: Bot, message: Message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.reply(
            f"**◈ ᴡʜᴀᴛ ꜱʜᴏᴜʟᴅ ɪ ᴡᴀʀᴍ ◈**\n\n"
            f">{E_USER} One line = artist, top `{ARTIST_LIMIT}` tracks\n"
            f">`/warm Arijit Singh`\n\n"
            f">{E_TRACK} Many lines = `{RESULTS_PER_SONG}` results each\n"
            f">`/warm Satranga Animal`\n"
            f">`Tauba Tauba Bad Newz`\n"
            f">`O Maahi Dunki`\n\n"
            f"__{E_SPARKLE} Up to `{MAX_LINES}` lines per request__"
        )
        return

    raw = parts[1].strip()
    lines = [l.strip() for l in raw.split("\n") if l.strip()]

    status = await message.reply(E_SEARCH)

    try:
        engine = SearchEngine()
        cache = CacheManager(client.db)

        queued = 0
        already = 0
        missed = 0
        skipped_lines = 0

        if len(lines) > 1:
            # ---- Song list mode: top N results for each line ----
            skipped_lines = max(0, len(lines) - MAX_LINES)

            for line in lines[:MAX_LINES]:
                try:
                    resp = await engine.search(line)
                    results = (resp.get("results") or [])[:RESULTS_PER_SONG]

                    if not results:
                        missed += 1
                        continue

                    for r in results:
                        vid = r.get("id")
                        if not vid:
                            continue

                        if await cache.get(vid):
                            already += 1
                            continue

                        if already_queued(vid):
                            continue

                        manual_queue.append({
                            "video_id": vid,
                            "title": r.get("title", "Unknown"),
                            "uploader": r.get("uploader", "Unknown"),
                        })
                        queued += 1

                except Exception as e:
                    logger.warning(f"warm: line '{line}' failed: {e}")
                    missed += 1

                await asyncio.sleep(3)

            label = f"`{len(lines[:MAX_LINES])}` songs"

        else:
            # ---- Artist mode: pull their catalogue ----
            artist = lines[0]
            resp = await engine.search(f"{artist} songs")
            results = (resp.get("results") or [])[:ARTIST_LIMIT]

            if not results:
                await status.edit_text(
                    f"**◈ ɴᴏᴛʜɪɴɢ ꜰᴏᴜɴᴅ ◈**\n\n"
                    f">{E_STOP} No tracks found for `{artist}`"
                )
                return

            for r in results:
                vid = r.get("id")
                if not vid:
                    continue

                if await cache.get(vid):
                    already += 1
                    continue

                if already_queued(vid):
                    continue

                manual_queue.append({
                    "video_id": vid,
                    "title": r.get("title", "Unknown"),
                    "uploader": r.get("uploader", artist),
                })
                queued += 1

            label = f"**{artist}**"

        if queued == 0:
            await status.edit_text(
                f"**◈ ɴᴏᴛʜɪɴɢ ᴛᴏ ǫᴜᴇᴜᴇ ◈**\n\n"
                f">{E_CHECK} Already cached `{already}`\n"
                f">{E_STOP} Not found `{missed}`"
            )
            return

        ensure_manual_worker(client)

        eta_min = (len(manual_queue) * (MIN_GAP + MAX_GAP) // 2) // 60
        eta = f"{eta_min // 60}h {eta_min % 60}m" if eta_min >= 60 else f"{eta_min}m"

        text = (
            f"**◈ ᴡᴀʀᴍɪɴɢ ǫᴜᴇᴜᴇᴅ ◈**\n\n"
            f">{E_USER} {label}\n"
            f">{E_DOWNLOAD} Queued `{queued}` new tracks\n"
            f">{E_CHECK} Already cached `{already}`\n"
        )

        if missed:
            text += f">{E_STOP} Not found `{missed}`\n"

        if skipped_lines:
            text += f">{E_SKIP} Over limit, ignored `{skipped_lines}`\n"

        text += (
            f">{E_CASSETTE} Queue total `{len(manual_queue)}`\n"
            f">{E_SHUFFLE} Roughly `{eta}` to finish\n\n"
            f"__{E_SPARKLE} Automatic warming pauses until this finishes__"
        )

        await status.edit_text(text)

    except Exception as e:
        logger.error(f"warm_artist error: {e}")
        await status.edit_text(f"**◈ ᴇʀʀᴏʀ ◈**\n\n>`{e}`")


@Bot.on_message(filters.command("warmstop") & filters.user(int(OWNER_ID)))
async def warm_stop(client: Bot, message: Message):
    """Clears the pending manual queue."""
    count = len(manual_queue)
    manual_queue.clear()

    await message.reply(
        f"**◈ ǫᴜᴇᴜᴇ ᴄʟᴇᴀʀᴇᴅ ◈**\n\n"
        f">{E_STOP} Dropped `{count}` pending tracks\n"
        f">{E_CHECK} Anything already cached stays cached"
    )


# =====================================================================
# OWNER PANEL
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

    if await voice_chat_busy():
        mode = f"{E_PHONE} Voice chat live — warming paused"
    elif manual_busy():
        mode = f"{E_DOWNLOAD} Manual warming — automatic paused"
    elif enabled:
        mode = f"{E_SHUFFLE} Automatic warming active"
    else:
        mode = f"{E_STOP} Idle"

    return (
        f"**◈ ᴄᴀᴄʜᴇ ᴡᴀʀᴍᴇʀ ◈**\n\n"
        f">{E_SETTINGS} Status {state}\n"
        f">{E_CASSETTE} Cached tracks `{total}`\n"
        f">{E_NEXT} Manual queue `{len(manual_queue)}`\n"
        f">{mode}\n"
        f">{E_SHUFFLE} Gap `{MIN_GAP//60}–{MAX_GAP//60}` min · rest `{CYCLE_REST//60}` min\n\n"
        f"__{E_SPARKLE} `/warm` to queue · `/warmstop` to clear__"
    )


@Bot.on_message(filters.command("warmer") & filters.user(int(OWNER_ID)))
async def warmer_panel(client: Bot, message: Message):
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