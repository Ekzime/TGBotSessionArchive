import logging
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers.auth_handlers import router as auth_router
from bot.handlers.give_tg_handler import router as give_tg_router
from bot.middlewares.auth_middleware import AuthMiddleware
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_API = os.getenv("TELEGRAM_BOT_API")

logging.basicConfig(level=logging.DEBUG)

async def main():
    bot = Bot(TELEGRAM_BOT_API)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем middleware для обработки всех сообщений
    dp.message.middleware(AuthMiddleware())

    dp.include_router(auth_router)
    dp.include_router(give_tg_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")