import logging
import asyncio
from settings.config import TELEGRAM_BOT_API
from aiogram import Bot, Dispatcher
from bot.handlers.auth_handlers import router as auth_router
from bot.middlewares.auth_middleware import AuthMiddleware

logging.basicConfig(level=logging.DEBUG)

async def main():
    bot = Bot(TELEGRAM_BOT_API)
    dp = Dispatcher()

    # Подключаем мидлварь для обработки всех сообщений
    dp.message.middleware(AuthMiddleware())

    dp.include_router(auth_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")