import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers.auth_handlers import router as auth_router
from bot.handlers.give_tg_handler import router as give_tg_router
from bot.handlers.take_tg_handler import router as take_rg_router
from bot.handlers.start_handler import router as start_router
from bot.handlers.view_tg_handdler import router as view_tg_router
from bot.handlers.info_handlers import router as info_chat_router
from bot.middlewares.auth_middleware import AuthMiddleware
from bot.core.bot_instance import bot
from bot.monitoring.telethon_service import run_monitoring

logging.basicConfig(level=logging.DEBUG)

async def on_sturtup():
    # Создаем фоновую задачу
    asyncio.create_task(run_monitoring())

async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AuthMiddleware())
    dp.include_router(auth_router)
    dp.include_router(start_router)
    dp.include_router(give_tg_router)
    dp.include_router(take_rg_router)
    dp.include_router(view_tg_router)
    dp.include_router(info_chat_router)

    await dp.start_polling(bot, on_sturtup=on_sturtup())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")