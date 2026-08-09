import logging
from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from jiosaavn.bot import Bot
from api.favorites import FavoritesManager
from api.cache import CacheManager

logger = logging.getLogger(__name__)


def favorite_button(video_id: str, is_fav: bool):
    if is_fav:
        return InlineKeyboardButton("💔 Remove Favorite", callback_data=f"fav_remove_{video_id}")
    return InlineKeyboardButton("❤️ Add to Favorites", callback_data=f"fav_add_{video_id}")


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

        await callback.answer("❤️ Added to Favorites!", show_alert=False)

        try:
            new_markup = InlineKeyboardMarkup([
                [favorite_button(video_id, is_fav=True)]
            ])
            await callback.edit_message_reply_markup(new_markup)
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

        await callback.answer("💔 Removed from Favorites", show_alert=False)

        try:
            new_markup = InlineKeyboardMarkup([
                [favorite_button(video_id, is_fav=False)]
            ])
            await callback.edit_message_reply_markup(new_markup)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"fav_remove error: {e}")
        await callback.answer("❌ Something went wrong.", show_alert=True)


@Bot.on_message(filters.command("myfavorites") & filters.private)
async def my_favorites(client: Bot, message: Message):
    try:
        favorites = FavoritesManager(client.db)
        songs = await favorites.list_favorites(message.from_user.id)

        if not songs:
            await message.reply("💔 Aapki favorites list khaali hai.\n\nKisi gaane ke neeche ❤️ button dabao usse add karne ke liye.")
            return

        buttons = []
        for song in songs:
            title = song.get("title", "Unknown")[:45]
            buttons.append([
                InlineKeyboardButton(f"🎵 {title}", callback_data=f"fav_play_{song['video_id']}")
            ])

        buttons.append([InlineKeyboardButton("Close ❌", callback_data="close")])

        await message.reply(
            f"❤️ **Your Favorites** ({len(songs)})\n\nGaane par tap karo sunne ke liye:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"myfavorites error: {e}")
        await message.reply(f"❌ Error: {e}")


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
            chat_id=callback.message.chat.id,   # 🔥 FIX: jahan se tap hua wahi bhejo (group/DM dono)
            audio=song["file_id"],
            title=song["title"],
            performer=song.get("uploader", "YouTube"),
            reply_markup=InlineKeyboardMarkup([
                [favorite_button(video_id, is_fav=True)],
                [InlineKeyboardButton("🎵 Search Again", switch_inline_query_current_chat="")],
                [InlineKeyboardButton("➕ Add me to your group", url="https://t.me/AartiMusic_bot?startgroup=true")]
            ])
        )

    except Exception as e:
        logger.error(f"fav_play error: {e}")
        await callback.answer("❌ Something went wrong.", show_alert=True)