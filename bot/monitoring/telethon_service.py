import asyncio
import logging
from typing import Dict

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from db.services.telegram_crud import (
    list_telegram_accounts_with_monitoring,
    create_telegram_message,
    mark_deleted_messages
)

logger = logging.getLogger(__name__)
import os
from dotenv import load_dotenv

load_dotenv()

API_TELETHON_ID = int(os.getenv("API_TELETHON_ID"))
API_TELETHON_HASH = os.getenv("API_TELETHON_HASH")
LOGS_GROUP_ID = -1002648817984 
CHECK_INTERVAL = 10           # раз в 10 секунд проверяем аккаунты

# Глобальный словарь: account_id -> client
active_clients: Dict[int, TelegramClient] = {}

async def run_monitoring():
    """
    Запускается в фоне. Каждые CHECK_INTERVAL секунд перечитывает аккаунты (is_monitoring=true).
    Поднимает недостающие клиенты, отключает те, у кого monitoring выключен.
    """
    while True:
        await asyncio.sleep(CHECK_INTERVAL)

        # 1. Берём список аккаунтов (dict) из CRUD, где is_monitoring=True
        accounts = list_telegram_accounts_with_monitoring()

        # Собираем id в сет для удобства
        current_ids = set(acc["id"] for acc in accounts)

        # 2. Запускаем клиентов, если их ещё нет
        for acc in accounts:
            acc_id = acc["id"]
            if acc_id not in active_clients:
                # Поднимаем Telethon-клиент
                client = await start_client_for_account(acc)
                active_clients[acc_id] = client
                logger.info(f"Запущен Telethon-клиент для account_id={acc_id}")

        # 3. Отключаем клиентов, которые больше не в списке is_monitoring
        for acc_id in list(active_clients.keys()):
            if acc_id not in current_ids:
                client = active_clients[acc_id]
                await client.disconnect()
                del active_clients[acc_id]
                logger.info(f"Отключен Telethon-клиент для account_id={acc_id}")


async def start_client_for_account(acc_dict: dict) -> TelegramClient:
    """
    Создаёт и подключает Telethon-клиент для одного аккаунта.
    Регистрирует обработчики (NewMessage, MessageDeleted).
    Возвращает client.
    """
    session_str = acc_dict["session_string"]
    account_id = acc_dict["id"]

    # Инициализируем клиент
    client = TelegramClient(StringSession(session_str), API_TELETHON_ID, API_TELETHON_HASH)

    await client.connect()
    if not await client.is_user_authorized():
        logger.warning(f"Аккаунт id={account_id} не авторизован, пропускаем.")
        return client  # Вы можете сделать дополнительные проверки

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
                    LOGS_GROUP_ID,
                    event.message,
                    chat_id
                )
                # Если это список, возьмём первый
                logs_msg_id = fwd.id if hasattr(fwd, "id") else fwd[0].id
                # Заменим текст заглушкой
                text = f"[{media_type}]"
            except Exception as e:
                logger.error(f"Не удалось переслать медиа в LOGS_GROUP: {e}")

        # Создаём запись в БД
        create_telegram_message(
            account_id=account_id,
            chat_id=chat_id,
            message_id=msg_id,
            sender_id=sender_id,
            text=text,
            date=date,
            logs_msg_id=logs_msg_id,
            media_type=media_type
        )

    @client.on(events.MessageDeleted())
    async def handler_deleted(event):
        """
        Срабатывает, когда сообщения удаляются.
        event.deleted_ids - список ID удалённых сообщений
        """
        deleted_ids = event.deleted_ids
        # Вызываем mark_deleted_messages
        mark_deleted_messages(account_id, deleted_ids)

    return client

