import asyncio
import logging
from typing import Dict

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
LOGS_GROUP_ID = settings.LOGS_GROUP_ID
CHECK_INTERVAL = settings.CHECK_INTERVAL

# Глобальный словарь: account_id -> client
active_clients: Dict[int, TelegramClient] = {}


async def run_monitoring():
    """
    Запускается в фоне. Каждые CHECK_INTERVAL секунд перечитывает аккаунты (is_monitoring=true).
    Поднимает недостающие клиенты, отключает те, у кого monitoring выключен.
    """
    logger.info(
        "run_monitoring: Запущен бесконечный цикл мониторинга. Timeout: {CHECK_INTERVAL}"
    )
    while True:
        logger.info("🔁 Проверка аккаунтов...")
        await asyncio.sleep(CHECK_INTERVAL)

        # 1. Берём список аккаунтов (dict) из CRUD, где is_monitoring=True
        try:
            accounts = list_telegram_accounts_with_monitoring()
        except Exception as e:
            logger.error(f"Ошибка при получении списка аккаунтов: {e}", exc_info=True)
            continue

        logger.info(
            "run_monitoring: Найдено аккаунтов для мониторинга: %d", len(accounts)
        )

        # Собираем id в сет для удобства
        current_ids = set(acc["id"] for acc in accounts)

        # 2. Запускаем клиентов, если их ещё нет
        for acc in accounts:
            acc_id = acc["id"]
            if acc_id not in active_clients:
                # Поднимаем Telethon-клиент
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

        # 3. Отключаем клиентов, которые больше не в списке is_monitoring
        for acc_id in list(active_clients.keys()):
            if acc_id not in current_ids:
                client = active_clients[acc_id]
                try:
                    await client.disconnect()
                    del active_clients[acc_id]
                    logger.info("Отключен Telethon-клиент для account_id=%d", acc_id)
                except Exception as e:
                    logger.error(
                        "Ошибка при отключении клиента account_id=%d: %s",
                        acc_id,
                        e,
                        exc_info=True,
                    )


async def start_client_for_account(acc_dict: dict) -> TelegramClient:
    """
    Создаёт и подключает Telethon-клиент для одного аккаунта.
    Регистрирует обработчики (NewMessage, MessageDeleted).
    Возвращает client.
    """
    session_str = acc_dict["session_string"]
    account_id = acc_dict["id"]

    client = TelegramClient(
        StringSession(session_str), API_TELETHON_ID, API_TELETHON_HASH
    )

    await client.connect()
    if not await client.is_user_authorized():
        logger.warning("Аккаунт id=%d не авторизован, пропускаем.", account_id)
        return client

    @client.on(events.NewMessage)
    async def handler_newmsg(event):
        """
        Срабатывает на каждое новое сообщение.
        Если есть медиа (voice, document, photo...), пересылаем в логовую группу.
        Сохраняем в БД через create_telegram_message.
        """
        chat_id = event.chat_id
        sender_id = event.sender_id
        msg_id = event.message.id
        date = event.message.date

        text = event.raw_text or ""
        logs_msg_id = None
        media_type = None

        # Проверяем, есть ли медиа (voice, document, photo, video, etc.)
        if event.message.voice:
            media_type = "voice"
        elif event.message.photo:
            media_type = "photo"
        elif event.message.document:
            media_type = "document"
        elif event.message.video:
            media_type = "video"

        if media_type:
            # Пересылаем в логовую группу
            try:
                # forward_messages возвращает Message или список
                fwd = await client.forward_messages(
                    LOGS_GROUP_ID, event.message, chat_id
                )
                # Если это список, возьмём первый
                logs_msg_id = fwd.id if hasattr(fwd, "id") else fwd[0].id
                # Заменим текст заглушкой
                text = f"[{media_type}]"
            except Exception as e:
                logger.error(f"Не удалось переслать медиа в LOGS_GROUP: {e}")

        # Создаём запись в БД
        try:
            create_telegram_message(
                account_id=account_id,
                chat_id=chat_id,
                message_id=msg_id,
                sender_id=sender_id,
                text=text,
                date=date,
                logs_msg_id=logs_msg_id,
                media_type=media_type,
            )
        except Exception as e:
            logger.error("Ошибка при записи сообщения в БД: %s", e, exc_info=True)

    @client.on(events.MessageDeleted())
    async def handler_deleted(event):
        """
        Срабатывает, когда сообщения удаляются.
        event.deleted_ids - список ID удалённых сообщений
        """
        deleted_ids = event.deleted_ids
        # Вызываем mark_deleted_messages
        try:
            mark_deleted_messages(account_id, deleted_ids)
        except Exception as e:
            logger.error(
                "Ошибка при отметке удалённых сообщений в БД: %s", e, exc_info=True
            )

    return client
