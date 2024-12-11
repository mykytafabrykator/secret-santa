import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from db import init_db
from handlers.group import register_group_handlers
from handlers.private import register_private_handlers

logging.basicConfig(level=logging.INFO)

async def main():
    # Отримуємо токен з env
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set in environment variables")

    await init_db()  # Ініціалізація БД і пулу з'єднань

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.bot = bot

    register_group_handlers(dp)
    register_private_handlers(dp)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
