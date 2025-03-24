import logging
import asyncio
import sys
from contextlib import suppress
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.monitoring.telethon_service import run_monitoring, active_clients
from bot.core.bot_instance import bot
from bot import root_router

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# хранение фоновой задачи
monitoring_task: asyncio.Task | None = None

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def on_startup():
    """Вызывается автоматически при старта бота"""
    global monitoring_task
    logger.info("Запуск фонового процесса (Telethon)")
    monitoring_task = asyncio.create_task(run_monitoring())


async def on_shutdown():
    """Вызывается автоматически при остановке бота"""
    global monitoring_task
    logger.info("Останновка фонового процесса (Telethon)")
    if monitoring_task:
        monitoring_task.cancel()
        with suppress(asyncio.CancelledError):
            await monitoring_task

    # отключение активных сессий telethon
    for acc_id, client in list(active_clients.items()):
        if client.is_connected():
            await client.disconnect()
        active_clients.pop(acc_id, None)
    logger.info("Все Telethon-клиенты отключены")


async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(root_router)

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
