import logging
from pyrogram import filters, enums
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from jiosaavn.bot import Bot
from jiosaavn.emojis import *
from api.favorites import FavoritesManager
from api.cache import CacheManager

logger = logging.getLogger(__name__)


def favorite_button(video_id: str, is_fav: bool):
    return InlineKeyboardButton(
        "ʀᴇᴍᴏᴠᴇ ꜰᴀᴠᴏʀɪᴛᴇ" if is_fav else "ᴀᴅᴅ ᴛᴏ ꜰᴀᴠᴏʀɪᴛᴇꜱ",
        callback_data=f"fav_remove_{video_id}" if is_fav else f"fav_add_{video_id}",
        style=enums.ButtonStyle.DANGER,
        icon_custom_emoji_id="5255861796350224063"
    )


def audio_markup(video_id: str, is_fav: bool):
    return InlineKeyboardMarkup([
        [favorite_button(video_id, is_fav)],
        [
            InlineKeyboardButton(
                "ꜱᴇᴀʀᴄʜ ᴀɢᴀɪɴ",
                switch_inline_query_current_chat="",
                style=enums.ButtonStyle.PRIMARY,
                icon_custom_emoji_id="6318752565865482087"
            )
        ],
        [
            InlineKeyboardButton(
                "ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                url="https://t.me/AartiMusic_bot?startgroup=true",
                style=enums.ButtonStyle.SUCCESS,
                icon_custom_emoji_id="5861735798956627072"
            )
        ]
    ])


@Bot.on_callback_query(filters.regex(r"^fav_add_"))
async def fav_add(client: Bot, callback: CallbackQuery):
    try:
        video_id = callback.data.replace("fav_add_", "")
        user_id = callback.from_user.id

        cache = CacheManager(client.db)
        favorites = FavoritesManager(client.db)

        song = await cache.get(video_id)
        if not song:
            await callback.answer("❌ Song data not found in cache.", show_alert=True)
            return

        await favorites.add(
            user_id=user_id,
            video_id=video_id,
            title=song["title"],
            file_id=song["file_id"],
            uploader=song.get("uploader", "")
        )

        await callback.answer("❤️ Added to your favorites!", show_alert=False)

        try:
            await callback.edit_message_reply_markup(
                InlineKeyboardMarkup([[favorite_button(video_id, is_fav=True)]])
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"fav_add error: {e}")
        await callback.answer("❌ Something went wrong.", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^fav_remove_"))
async def fav_remove(client: Bot, callback: CallbackQuery):
    try:
        video_id = callback.data.replace("fav_remove_", "")
        user_id = callback.from_user.id

        favorites = FavoritesManager(client.db)
        await favorites.remove(user_id, video_id)

        await callback.answer("💔 Removed from your favorites", show_alert=False)

        try:
            await callback.edit_message_reply_markup(
                InlineKeyboardMarkup([[favorite_button(video_id, is_fav=False)]])
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"fav_remove error: {e}")
        await callback.answer("❌ Something went wrong.", show_alert=True)


@Bot.on_message(filters.command("myfavorites"))
async def my_favorites(client: Bot, message: Message):
    try:
        favorites = FavoritesManager(client.db)
        songs = await favorites.list_favorites(message.from_user.id)

        if not songs:
            await message.reply(
                f"**◈ ʏᴏᴜʀ ᴠᴀᴜʟᴛ ɪꜱ ᴇᴍᴘᴛʏ ◈**\n\n"
                f">{E_HEART} You haven't saved any tracks yet.\n"
                f">Tap the ꜰᴀᴠᴏʀɪᴛᴇ button under any\n"
                f">song to start your collection.\n\n"
                f"__{E_SPARKLE} Then use `/favshuffle` to play them all__"
            )
            return

        buttons = []
        for song in songs:
            title = song.get("title", "Unknown")[:50]
            buttons.append([
                InlineKeyboardButton(
                    title,
                    callback_data=f"fav_play_{song['video_id']}",
                    style=enums.ButtonStyle.PRIMARY,
                    icon_custom_emoji_id="5911274703367968100"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "ᴄʟᴏꜱᴇ",
                callback_data="close",
                style=enums.ButtonStyle.DANGER,
                icon_custom_emoji_id="5974083768233760323"
            )
        ])

        await message.reply(
            f"**◈ ʏᴏᴜʀ ᴠᴀᴜʟᴛ ◈**\n\n"
            f">{E_HEARTS} `{len(songs)}` saved tracks\n\n"
            f"__{E_SPARKLE} Tap any track to play it__",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"myfavorites error: {e}")
        await message.reply(f"**◈ ᴇʀʀᴏʀ ◈**\n\n>`{e}`")


@Bot.on_callback_query(filters.regex(r"^fav_play_"))
async def fav_play(client: Bot, callback: CallbackQuery):
    try:
        video_id = callback.data.replace("fav_play_", "")
        cache = CacheManager(client.db)

        song = await cache.get(video_id)
        if not song:
            await callback.answer("❌ Song no longer available.", show_alert=True)
            return

        await callback.answer()

        await client.send_audio(
            chat_id=callback.message.chat.id,
            audio=song["file_id"],
            title=song["title"],
            performer=song.get("uploader", "YouTube"),
            reply_markup=audio_markup(video_id, is_fav=True)
        )

    except Exception as e:
        logger.error(f"fav_play error: {e}")
        await callback.answer("❌ Something went wrong.", show_alert=True)