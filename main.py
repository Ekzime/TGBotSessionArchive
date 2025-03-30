import sys
import logging
import asyncio
from contextlib import suppress
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.monitoring.telethon_service import run_monitoring, active_clients
from bot.core.bot_instance import bot
from bot import root_router
from db.services.user_crud import create_admin_account
from config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ADMIN_USERNAME = settings.ADMIN_USERNAME
ADMIN_PASSWORD = settings.ADMIN_PASSWORD

monitoring_task: asyncio.Task | None = None

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def on_startup():
    """Вызывается автоматически при старте бота"""
    global monitoring_task
    monitoring_task = asyncio.create_task(run_monitoring())


async def on_shutdown():
    """Вызывается автоматически при остановке бота"""
    global monitoring_task
    logger.info("on_shutdown: Остановка фонового процесса (Telethon)")
    if monitoring_task:
        monitoring_task.cancel()
        
        with suppress(asyncio.CancelledError):
            await monitoring_task

    # Отключение активных сессий Telethon
    for acc_id, client in list(active_clients.items()):
        if client.is_connected():
            await client.disconnect()
        active_clients.pop(acc_id, None)
    logger.info("on_shutdown: Все Telethon-клиенты отключены")


async def init_admin():
    create_admin_account(
        username=ADMIN_USERNAME, password=ADMIN_PASSWORD, is_admin=True
    )


async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(root_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await init_admin()

    try:
        # Запуск поллинга. При корректном завершении on_shutdown будет вызван автоматически.
        await dp.start_polling(bot)
    finally:
        # Гарантированно вызов shutdown и закрываем хранилище
        dp.shutdown()
        await dp.storage.close()


if __name__ == "__main__":
    asyncio.run(main())
