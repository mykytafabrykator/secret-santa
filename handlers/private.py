from aiogram import Bot, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from db import get_pool
from states import WishlistStates
from aiogram.fsm.context import FSMContext

async def is_admin(message: Message, bot: Bot) -> bool:
    if message.chat.type not in ("group", "supergroup"):
        return False
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ("administrator", "creator")

async def cmd_start_private(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.full_name if message.from_user.full_name else message.from_user.username

    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("""
        INSERT INTO users (user_id, username, started_pm) VALUES ($1,$2,1)
        ON CONFLICT (user_id) DO UPDATE SET started_pm=1, username=$2
        """, user_id, username)

    # Кнопки: Редагувати wishlist, Профіль, Мій одержувач
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✍️Редагувати wishlist"), KeyboardButton(text="🎒Профіль")],
            [KeyboardButton(text="🎅Мій одержувач")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await message.answer(
        "❄️Вітаю!\n\n☃️Скористайтеся кнопками нижче:",
        reply_markup=keyboard
    )

async def start_wishlist_edit(message: Message, state: FSMContext):
    await message.answer("✍️Введіть свій wishlist.\n/cancel - скасувати")
    await state.set_state(WishlistStates.entering)

async def cancel_wishlist(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.")

async def save_wishlist(message: Message, state: FSMContext):
    wishlist_text = message.text.strip()
    user_id = message.from_user.id
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET wishlist = $1 WHERE user_id = $2", wishlist_text, user_id)
    await state.clear()
    await message.answer("✨Ваш wishlist збережено!")

async def show_profile(message: Message, bot: Bot):
    user_id = message.from_user.id
    p = await get_pool()
    async with p.acquire() as conn:
        user_row = await conn.fetchrow("SELECT wishlist FROM users WHERE user_id = $1", user_id)
        wishlist = user_row["wishlist"] if user_row else None

        parts = await conn.fetch("""
        SELECT p.chat_id, p.assigned_to, u.username AS receiver_username
        FROM participants p
        LEFT JOIN users u ON p.assigned_to = u.user_id
        WHERE p.user_id = $1
        """, user_id)

    profile_text = "🎒Ваш профіль:\n\n"
    profile_text += f"✨Ваш wishlist:\n{wishlist if wishlist else 'не заповнений'}\n\n"

    if parts:
        assigned_info = []
        for part in parts:
            if part["assigned_to"]:
                assigned_info.append(f"Чат {part['chat_id']}: ви даруєте {part['receiver_username']}")
        if assigned_info:
            profile_text += "\n".join(assigned_info)
        else:
            profile_text += "Ще ніхто не випав."
    else:
        profile_text += "Ви поки що не приєднувались до жодної гри."

    await message.answer(profile_text)

async def show_assigned_wishlist(message: Message, bot: Bot):
    user_id = message.from_user.id
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("""
        SELECT p.assigned_to, u2.username AS assigned_name, u2.wishlist AS assigned_wishlist
        FROM participants p
        JOIN users u ON p.user_id = u.user_id
        LEFT JOIN users u2 ON p.assigned_to = u2.user_id
        WHERE p.user_id = $1
        """, user_id)

    if not rows:
        await message.answer("Ви не брали участь в жодній грі або ще нікого не призначено.")
        return

    assigned_entries = [r for r in rows if r["assigned_to"] is not None]

    if not assigned_entries:
        await message.answer("Ще ніхто не призначений вам.")
        return

    assigned_entry = assigned_entries[0]
    assigned_name = assigned_entry["assigned_name"]
    assigned_wishlist = assigned_entry["assigned_wishlist"]

    if assigned_wishlist:
        text = f"🎅🏻Ти таємний Санта для: {assigned_name}\n\n🎁Його(її) wishlist:\n\n{assigned_wishlist}"
    else:
        text = f"Вам призначено користувача: {assigned_name}, але wishlist не заповнений."

    await message.answer(text)

async def unknown_private_message(message: Message):
    await message.answer("Помилка: Невідома команда або запит.")

def register_private_handlers(dp):
    dp.message.register(cmd_start_private, Command("start"), F.chat.type == "private")
    dp.message.register(start_wishlist_edit, F.text == "✍️Редагувати wishlist", F.chat.type == "private")
    dp.message.register(show_profile, F.text == "🎒Профіль", F.chat.type == "private")
    dp.message.register(show_assigned_wishlist, F.text == "🎅Мій одержувач", F.chat.type == "private")
    dp.message.register(cancel_wishlist, Command("cancel"), WishlistStates.entering)
    dp.message.register(save_wishlist, F.text, WishlistStates.entering)
    dp.message.register(unknown_private_message, F.chat.type == "private")
