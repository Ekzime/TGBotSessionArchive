import os
import asyncio
import logging
from typing import Dict, Optional

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import settings
from db.services.telegram_crud import (
    list_telegram_accounts_with_monitoring,
    create_telegram_message,
    mark_deleted_messages,
)

logger = logging.getLogger(__name__)

API_TELETHON_ID = settings.API_TELETHON_ID
API_TELETHON_HASH = settings.API_TELETHON_HASH
CHECK_INTERVAL = settings.CHECK_INTERVAL
MEDIA_ROOT = os.path.join(settings.BASE_DIR, "media")

# Глобальный словарь: account_id -> client
active_clients: Dict[int, TelegramClient] = {}


async def run_monitoring():
    """
    Бесконечный цикл, который:
      1. Каждые CHECK_INTERVAL секунд перечитывает логовую группу из БД.
      2. Получает аккаунты для мониторинга.
      3. Поднимает отсутствующие клиенты, отключает лишние.
      4. Проверяет, авторизован ли клиент (если нет – отключает).
    """

    logger.info(
        "run_monitoring: Запущен цикл мониторинга (интервал %s сек.)", CHECK_INTERVAL
    )

    while True:
        # 2. Получаем список аккаунтов для мониторинга
        try:
            accounts = list_telegram_accounts_with_monitoring()
        except Exception as e:
            logger.error("Ошибка при получении списка аккаунтов: %s", e, exc_info=True)
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        logger.info(
            "run_monitoring: Найдено аккаунтов для мониторинга: %d", len(accounts)
        )
        current_ids = set(acc["id"] for acc in accounts)

        # 3. Поднимаем клиентов, если их ещё нет
        for acc in accounts:
            acc_id = acc["id"]
            if acc_id not in active_clients:
                try:
                    client = await start_client_for_account(acc)
                    active_clients[acc_id] = client
                    logger.info("Запущен Telethon-клиент для account_id=%d", acc_id)
                except Exception as e:
                    logger.error(
                        "Ошибка при запуске клиента для account_id=%d: %s",
                        acc_id,
                        e,
                        exc_info=True,
                    )

        # 4. Отключаем клиентов, которых нет в списке (monitoring выключен)
        for acc_id in list(active_clients.keys()):
            if acc_id not in current_ids:
                client = active_clients[acc_id]
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.error(
                        "Ошибка при отключении клиента account_id=%d: %s",
                        acc_id,
                        e,
                        exc_info=True,
                    )
                del active_clients[acc_id]
                logger.info("Отключен Telethon-клиент для account_id=%d", acc_id)

        # 5. Проверяем, подключён и авторизован ли клиент, если нет – отключаем
        for acc_id, client in list(active_clients.items()):
            if not client.is_connected():
                logger.warning(
                    "Client for account_id=%d не is_connected(), отключаем", acc_id
                )
                await client.disconnect()
                del active_clients[acc_id]
                continue
            if not await client.is_user_authorized():
                logger.warning("Аккаунт id=%d не авторизован, отключаем", acc_id)
                await client.disconnect()
                del active_clients[acc_id]
                continue

        await asyncio.sleep(CHECK_INTERVAL)


async def start_client_for_account(acc_dict: dict) -> TelegramClient:
    session_str = acc_dict["session_string"]
    account_id = acc_dict["id"]

    client = TelegramClient(
        StringSession(session_str), settings.API_TELETHON_ID, settings.API_TELETHON_HASH
    )
    await client.connect()

    if not await client.is_user_authorized():
        logger.warning("Аккаунт id=%d не авторизован, пропускаем.", account_id)
        return client

    # Создаем папку заранее
    os.makedirs(MEDIA_ROOT, exist_ok=True)

    @client.on(events.NewMessage)
    async def handler_newmsg(event):
        if not event.is_private:
            return

        chat_id = event.chat_id
        sender_id = event.sender_id
        msg_id = event.message.id
        date = event.message.date

        chat_name = None
        try:
            chat = await event.get_chat()
            chat_name = getattr(chat, "first_name", None) or getattr(
                chat, "username", None
            )
        except Exception as e:
            logger.warning("Ошибка при получении имени чата: %s", e)

        text = event.raw_text or ""
        media_type = None
        media_path = None

        # Определяем тип медиа
        if event.message.voice:
            media_type = "voice"
        elif event.message.photo:
            media_type = "photo"
        elif event.message.document:
            media_type = "document"
        elif event.message.video:
            media_type = "video"

        # Сохраняем медиа-файл
        if media_type:
            media_folder = os.path.join(MEDIA_ROOT, str(account_id), str(chat_id))
            os.makedirs(media_folder, exist_ok=True)

            # Автоматически расширение добавится само
            media_file_path = await event.message.download_media(file=media_folder)
            if media_file_path:
                media_path = media_file_path
                text = f"[{media_type}]"
            else:
                logger.error("Не удалось сохранить медиа файл для сообщения %d", msg_id)

        try:
            create_telegram_message(
                account_id=account_id,
                chat_id=chat_id,
                chat_name=chat_name,
                message_id=msg_id,
                sender_id=sender_id,
                text=text,
                date=date,
                logs_msg_id=None,
                media_type=media_type,
                media_path=media_path,
            )
        except Exception as e:
            logger.error("Ошибка при записи сообщения в БД: %s", e, exc_info=True)

    @client.on(events.MessageDeleted())
    async def handler_deleted(event):
        deleted_ids = event.deleted_ids
        try:
            mark_deleted_messages(account_id, deleted_ids)
        except Exception as e:
            logger.error(
                "Ошибка при отметке удалённых сообщений в БД: %s", e, exc_info=True
            )

    return client
