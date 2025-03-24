import logging
import asyncio
from contextlib import suppress
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
from bot.monitoring.telethon_service import run_monitoring, active_clients

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# хранение фоновой задачи
monitoring_task: asyncio.Task | None = None

async def on_startup():
    global monitoring_task
    logger.info("Запуск фонового процесса (Telethon)")
    monitoring_task = asyncio.create_task(run_monitoring())

async def on_shutdown():
    """ Этот колбэк будет вызван aiogram автоматически при остановке бота"""
    global monitoring_task
    logger.info("Останновка фонового процесса (Telethon)")
    if monitoring_task:
        monitoring_task.cancel()
        with suppress(asyncio.CancelledError):
            await monitoring_task
    
    for acc_id, client in list(active_clients.items()):
        if client.is_connected():
            await client.disconnect()
        active_clients.pop(acc_id, None)
    logger.info("Все Telethon-клиенты отключены")


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

    # Регистрируем колбэки старта и остановки фонового процесса мониторинга
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Routers are connected.")

    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopping by Ctrl+C")
