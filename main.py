import logging
import asyncio
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers.auth_handlers import router as auth_router
from bot.handlers.give_tg_handler import router as give_tg_router
from bot.handlers.take_tg_handler import router as take_rg_router
from bot.handlers.start_handler import router as start_router
from bot.handlers.view_tg_handdler import router as view_tg_router
from bot.handlers.info_handlers import router as info_chat_router
from bot.middlewares.auth_middleware import AuthMiddleware
from bot.callbacks.callbacks import router as callback_router
from bot.core.bot_instance import bot

logging.basicConfig(level=logging.DEBUG)  # <-- вызывается из logging, не из logger
logger = logging.getLogger(__name__)

async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AuthMiddleware())
    dp.include_router(auth_router)
    dp.include_router(start_router)
    dp.include_router(give_tg_router)
    dp.include_router(take_rg_router)
    dp.include_router(view_tg_router)
    dp.include_router(info_chat_router)
    dp.include_router(callback_router)
    logger.info("Routers are connected.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        logger.info("Bot running...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stoping...")
