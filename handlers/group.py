from aiogram import Bot, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from db import get_pool, is_session_active, set_session_active, clear_participants
from utils import derangement
from handlers.private import is_admin


async def cmd_start_group(message: Message, bot: Bot):
    chat_id = message.chat.id
    if await is_session_active(chat_id):
        await message.answer("Наразі вже є активна сесія. Спершу закінчіть або відмініть поточну.")
        return

    await set_session_active(chat_id, True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅Приєднатись", callback_data="join")],
        [InlineKeyboardButton(text="🔔Закінчити", callback_data="end"),
         InlineKeyboardButton(text="‼️Відмінити", callback_data="cancel")]
    ])
    await message.answer("🥸Учасники:", reply_markup=keyboard)


async def join_callback(callback_query: CallbackQuery, bot: Bot):
    chat_id = callback_query.message.chat.id
    user = callback_query.from_user
    user_id = user.id

    if not await is_session_active(chat_id):
        await callback_query.answer("Наразі немає активної сесії для приєднання.", show_alert=True)
        return

    p = await get_pool()
    async with p.acquire() as conn:
        user_row = await conn.fetchrow("SELECT wishlist, started_pm FROM users WHERE user_id = $1", user_id)

    if not user_row or user_row["started_pm"] == 0 or not user_row["wishlist"]:
        await callback_query.answer("Ви повинні спершу почати діалог з ботом у приваті та заповнити свій wishlist!",
                                    show_alert=True)
        return

    async with p.acquire() as conn:
        p_row = await conn.fetchrow("SELECT user_id FROM participants WHERE chat_id = $1 AND user_id = $2", chat_id,
                                    user_id)
        if p_row:
            await callback_query.answer("Вас вже приєднано!", show_alert=True)
            return
        else:
            await conn.execute("INSERT INTO participants (chat_id, user_id) VALUES ($1, $2)", chat_id, user_id)

        rows = await conn.fetch("""
        SELECT u.username
        FROM participants p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.chat_id = $1
        """, chat_id)

    user_list_str = "\n".join([f"- {r['username']}" for r in rows])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅Приєднатись", callback_data="join")],
        [InlineKeyboardButton(text="🔔Закінчити", callback_data="end"),
         InlineKeyboardButton(text="‼️Відмінити", callback_data="cancel")]
    ])
    await callback_query.message.edit_text(
        text=f"🥸Учасники:\n{user_list_str}",
        reply_markup=keyboard
    )
    await callback_query.answer()


async def end_callback(callback_query: CallbackQuery, bot: Bot):
    message = callback_query.message
    if not await is_admin(message, bot):
        await callback_query.answer("Тільки адміністратор може завершити сесію!", show_alert=True)
        return

    chat_id = message.chat.id
    if not await is_session_active(chat_id):
        await callback_query.answer("Немає активної сесії для завершення.", show_alert=True)
        return

    p = await get_pool()
    async with p.acquire() as conn:
        participants_list = await conn.fetch("""
        SELECT u.user_id, u.username, u.started_pm, u.wishlist
        FROM participants p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.chat_id = $1
        """, chat_id)

    if not participants_list:
        await callback_query.answer("Немає учасників для розподілу.", show_alert=True)
        return

    user_ids = [row["user_id"] for row in participants_list]
    assigned = derangement(user_ids)
    if not assigned:
        await callback_query.answer("Не вдалося створити унікальний розподіл, спробуйте ще раз.", show_alert=True)
        return

    async with p.acquire() as conn:
        for giver_id, receiver_id in zip(user_ids, assigned):
            await conn.execute("UPDATE participants SET assigned_to = $1 WHERE chat_id = $2 AND user_id = $3",
                               receiver_id, chat_id, giver_id)
        # Отримуємо словник даних
        id_to_data = {row["user_id"]: (row["username"], row["wishlist"], row["started_pm"]) for row in
                      participants_list}

    # Розсилаємо повідомлення
    for giver_id, receiver_id in zip(user_ids, assigned):
        _, _, giver_started_pm = id_to_data[giver_id]
        receiver_username, receiver_wishlist, _ = id_to_data[receiver_id]

        if giver_started_pm:
            text = f"🎅🏻Ти таємний Санта для: {receiver_username}\n\n"
            if receiver_wishlist:
                text += f"🎁Його(її) wishlist:\n\n{receiver_wishlist}"
            else:
                text += "\nWishlist ще не заповнений."
            try:
                await bot.send_message(chat_id=giver_id, text=text)
            except Exception:
                pass

    await set_session_active(chat_id, False)
    await callback_query.message.edit_text("Розподіл завершено! Сесію завершено.")
    await callback_query.answer()


async def cancel_callback(callback_query: CallbackQuery, bot: Bot):
    message = callback_query.message
    if not await is_admin(message, bot):
        await callback_query.answer("Тільки адміністратор може відмінити сесію!", show_alert=True)
        return

    chat_id = message.chat.id
    if not await is_session_active(chat_id):
        await callback_query.answer("Немає активної сесії для скасування.", show_alert=True)
        return

    await clear_participants(chat_id)
    await set_session_active(chat_id, False)
    await callback_query.message.edit_text("Сесію відмінено. Ви можете запустити нову командою /start.")
    await callback_query.answer()


def register_group_handlers(dp):
    dp.message.register(cmd_start_group, Command("start"), (F.chat.type == "group") | (F.chat.type == "supergroup"))
    dp.callback_query.register(join_callback, F.data == "join",
                               (F.message.chat.type == "group") | (F.message.chat.type == "supergroup"))
    dp.callback_query.register(end_callback, F.data == "end",
                               (F.message.chat.type == "group") | (F.message.chat.type == "supergroup"))
    dp.callback_query.register(cancel_callback, F.data == "cancel",
                               (F.message.chat.type == "group") | (F.message.chat.type == "supergroup"))
