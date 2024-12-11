from aiogram import F, Bot
from aiogram.types import CallbackQuery, Message
from states import WishlistStates
from db import get_db
from aiogram.fsm.context import FSMContext

async def wishlist_callback(callback_query: CallbackQuery, bot: Bot, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Введіть свій wishlist.\n/cancel - скасувати")
    await state.set_state(WishlistStates.entering)

async def save_wishlist(message: Message, state: FSMContext):
    wishlist_text = message.text.strip()
    user_id = message.from_user.id
    async with get_db() as db:
        await db.execute("UPDATE users SET wishlist = ? WHERE user_id = ?", (wishlist_text, user_id))
        await db.commit()
    await state.clear()
    await message.answer("Ваш wishlist збережено!")

async def cancel_wishlist(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.")

def register_wishlist_handlers(dp):
    from aiogram.filters import Command
    dp.callback_query.register(wishlist_callback, F.data == "edit_wishlist", F.message.chat.type=="private")
    dp.message.register(cancel_wishlist, Command("cancel"), WishlistStates.entering)
    dp.message.register(save_wishlist, F.text, WishlistStates.entering)
