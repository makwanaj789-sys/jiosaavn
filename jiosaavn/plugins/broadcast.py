import asyncio
import logging
import time

from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    InputUserDeactivated,
    UserDeactivated,
    PeerIdInvalid,
    ChatWriteForbidden,
    ChannelPrivate,
    ChatAdminRequired,
)

from jiosaavn.bot import Bot
from jiosaavn.emojis import *
from jiosaavn.config.settings import OWNER_ID

logger = logging.getLogger(__name__)

SEND_DELAY = 0.12        # ~8 messages/sec — safely under Telegram's limits
PROGRESS_EVERY = 25      # update the status message this often

# Errors that mean the chat is gone for good — clean it out of the DB
DEAD_CHAT = (
    UserIsBlocked,
    InputUserDeactivated,
    UserDeactivated,
    PeerIdInvalid,
    ChannelPrivate,
)

# Errors that are temporary or permission-related — keep the chat, just skip
SKIP_CHAT = (
    ChatWriteForbidden,
    ChatAdminRequired,
)

_running = False
_cancel = False


def is_owner(user_id: int) -> bool:
    return bool(user_id and OWNER_ID and user_id == int(OWNER_ID))


def cancel_markup():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("ꜱᴛᴏᴘ ʙʀᴏᴀᴅᴄᴀꜱᴛ", callback_data="bc_cancel")
    ]])


def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def progress_text(target: str, done: int, total: int, sent: int, failed: int, removed: int, elapsed: float):
    pct = int((done / total) * 100) if total else 0
    filled = pct // 10
    bar = "█" * filled + "░" * (10 - filled)

    return (
        f"**◈ ʙʀᴏᴀᴅᴄᴀꜱᴛɪɴɢ ◈**\n\n"
        f">{E_MEGA} Target **{target}**\n"
        f">`{bar}` `{pct}%`\n"
        f">{E_NEXT} Progress `{done}/{total}`\n"
        f">{E_CHECK} Sent `{sent}`\n"
        f">{E_STOP} Failed `{failed}`\n"
        f">{E_SKIP} Removed `{removed}`\n"
        f">{E_SHUFFLE} Elapsed `{fmt_time(elapsed)}`"
    )


def summary_text(target: str, total: int, sent: int, failed: int, removed: int, elapsed: float, stopped: bool):
    head = "◈ ʙʀᴏᴀᴅᴄᴀꜱᴛ ꜱᴛᴏᴘᴘᴇᴅ ◈" if stopped else "◈ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇ ◈"

    return (
        f"**{head}**\n\n"
        f">{E_MEGA} Target **{target}**\n"
        f">{E_CASSETTE} Total `{total}`\n"
        f">{E_CHECK} Delivered `{sent}`\n"
        f">{E_STOP} Failed `{failed}`\n"
        f">{E_SKIP} Removed from DB `{removed}`\n"
        f">{E_SHUFFLE} Took `{fmt_time(elapsed)}`"
    )


async def run_broadcast(client: Bot, status: Message, source: Message, chat_ids: list, target: str, is_group: bool):
    global _running, _cancel

    total = len(chat_ids)
    sent = failed = removed = 0
    started = time.time()

    for index, chat_id in enumerate(chat_ids, start=1):
        if _cancel:
            break

        try:
            await source.copy(chat_id)
            sent += 1

        except FloodWait as e:
            # Telegram is telling us to slow down — wait it out, then retry once
            logger.warning(f"BROADCAST: FloodWait {e.value}s")
            await asyncio.sleep(e.value + 1)
            try:
                await source.copy(chat_id)
                sent += 1
            except Exception:
                failed += 1

        except DEAD_CHAT:
            failed += 1
            removed += 1
            try:
                if is_group:
                    await client.db.delete_group(chat_id)
                else:
                    await client.db.delete_user(chat_id)
            except Exception:
                pass

        except SKIP_CHAT:
            failed += 1

        except Exception as e:
            failed += 1
            logger.warning(f"BROADCAST: {chat_id} failed — {type(e).__name__}: {e}")

        if index % PROGRESS_EVERY == 0 or index == total:
            try:
                await status.edit_text(
                    progress_text(target, index, total, sent, failed, removed, time.time() - started),
                    reply_markup=cancel_markup()
                )
            except Exception:
                pass

        await asyncio.sleep(SEND_DELAY)

    elapsed = time.time() - started
    stopped = _cancel

    _running = False
    _cancel = False

    try:
        await status.edit_text(
            summary_text(target, total, sent, failed, removed, elapsed, stopped),
            reply_markup=None
        )
    except Exception:
        pass

    logger.info(f"📣 BROADCAST done — {sent}/{total} sent, {failed} failed, {removed} removed")


async def start_broadcast(client: Bot, message: Message, mode: str):
    global _running, _cancel

    if not message.from_user or not is_owner(message.from_user.id):
        return

    if _running:
        await message.reply(
            f"**◈ ᴀʟʀᴇᴀᴅʏ ʀᴜɴɴɪɴɢ ◈**\n\n"
            f">{E_STOP} A broadcast is in progress.\n"
            f">Stop it first, then try again."
        )
        return

    if not message.reply_to_message:
        await message.reply(
            f"**◈ ɴᴏᴛʜɪɴɢ ᴛᴏ ꜱᴇɴᴅ ◈**\n\n"
            f">{E_WRITE} Reply to the message you want to broadcast.\n\n"
            f">`/broadcast` — all users\n"
            f">`/broadcastgroups` — all groups\n"
            f">`/broadcastall` — everyone"
        )
        return

    try:
        if mode == "users":
            chat_ids = await client.db.get_all_users()
            target, is_group = "Users", False
        elif mode == "groups":
            chat_ids = await client.db.get_all_groups()
            target, is_group = "Groups", True
        else:
            users = await client.db.get_all_users()
            groups = await client.db.get_all_groups()
            chat_ids = users + groups
            target, is_group = "Everyone", False
    except Exception as e:
        await message.reply(f"**◈ ᴇʀʀᴏʀ ◈**\n\n>`{e}`")
        return

    if not chat_ids:
        await message.reply(
            f"**◈ ɴᴏ ʀᴇᴄɪᴘɪᴇɴᴛꜱ ◈**\n\n"
            f">{E_STOP} Nothing stored for **{target}** yet."
        )
        return

    eta = fmt_time(len(chat_ids) * SEND_DELAY)

    status = await message.reply(
        f"**◈ ꜱᴛᴀʀᴛɪɴɢ ʙʀᴏᴀᴅᴄᴀꜱᴛ ◈**\n\n"
        f">{E_MEGA} Target **{target}**\n"
        f">{E_CASSETTE} Recipients `{len(chat_ids)}`\n"
        f">{E_SHUFFLE} Roughly `{eta}`",
        reply_markup=cancel_markup()
    )

    _running = True
    _cancel = False

    asyncio.create_task(
        run_broadcast(client, status, message.reply_to_message, chat_ids, target, is_group)
    )


@Bot.on_message(filters.command("broadcast") & filters.private & filters.user(int(OWNER_ID)))
async def broadcast_users(client: Bot, message: Message):
    await start_broadcast(client, message, "users")


@Bot.on_message(filters.command("broadcastgroups") & filters.private & filters.user(int(OWNER_ID)))
async def broadcast_groups(client: Bot, message: Message):
    await start_broadcast(client, message, "groups")


@Bot.on_message(filters.command("broadcastall") & filters.private & filters.user(int(OWNER_ID)))
async def broadcast_all(client: Bot, message: Message):
    await start_broadcast(client, message, "all")


@Bot.on_callback_query(filters.regex(r"^bc_cancel$"))
async def broadcast_cancel(client: Bot, callback: CallbackQuery):
    global _cancel

    if not is_owner(callback.from_user.id):
        await callback.answer("🔒 Owner only.", show_alert=True)
        return

    if not _running:
        await callback.answer("Nothing is running.", show_alert=True)
        return

    _cancel = True
    await callback.answer("⏹️ Stopping after the current message…", show_alert=True)