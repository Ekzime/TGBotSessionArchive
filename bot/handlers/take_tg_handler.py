import asyncio
import re
import logging
import os
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.filters import Command
from telethon import TelegramClient, events
from telethon.errors import SessionRevokedError, FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.account import GetAuthorizationsRequest

from bot.core.bot_instance import bot
from db.services.telegram_crud import (
    get_telegram_account_by_alias,
    delete_telegram_account,
)
from db.models.model import User
from dotenv import load_dotenv

load_dotenv()
API_TELETHON_ID = int(os.getenv("API_TELETHON_ID"))
API_TELETHON_HASH = os.getenv("API_TELETHON_HASH")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = Router()

async def poll_for_new_session(
    client: TelegramClient,
    initial_count: int,
    alias: str,
    phone: str,
    chat_id: int,
    max_duration: int = 60
):
    """
    Периодически проверяет, не появилось ли больше сессий, чем было при старте (initial_count).
    Если да — считаем, что пользователь зашёл (авторизовался где-то ещё),
    удаляем аккаунт из БД и завершаем работу клиента.

    :param client: Экземпляр Telethon клиента
    :param initial_count: Исходное количество активных сессий
    :param alias: Alias аккаунта в БД
    :param phone: Телефон аккаунта
    :param chat_id: ID чата, куда отправлять сообщения пользователю
    :param max_duration: Максимальное время в секундах, в течение которого мы ждём появления новой сессии
    """
    end_time = datetime.utcnow() + timedelta(seconds=max_duration)
    while datetime.utcnow() < end_time:
        await asyncio.sleep(5)  # Интервал опроса
        try:
            auth_result = await client(GetAuthorizationsRequest())
            current_count = len(auth_result.authorizations)
        except SessionRevokedError:
            # Сессию аннулировали (Terminate all sessions)
            logger.warning(f"Session revoked for alias={alias}, phone={phone}")
            await bot.send_message(chat_id, f"Сессия аккаунта <b>{alias}</b> отозвана. Удаляем из БД.", parse_mode="HTML")
            delete_telegram_account(alias, phone)
            await client.disconnect()
            return
        except FloodWaitError as e:
            # Telegram просит подождать e.seconds
            logger.warning(f"FloodWaitError: нужно подождать {e.seconds} сек. alias={alias}, phone={phone}")
            await asyncio.sleep(e.seconds)
            continue
        except Exception as e:
            logger.exception(f"Ошибка при GetAuthorizationsRequest: {e}")
            # Не завершаем клиент сразу, но сообщаем в чат
            await bot.send_message(chat_id, f"Ошибка при проверке сессий: {e}")
            return

        if current_count > initial_count:
            # Новая сессия обнаружена
            logger.info(f"New session detected for alias={alias}, phone={phone}")
            delete_telegram_account(alias, phone)
            await bot.send_message(
                chat_id,
                f"Аккаунт <b>{alias}</b> удалён из БД (обнаружена новая сессия).",
                parse_mode="HTML"
            )
            await client.disconnect()
            return

    # Если мы дошли сюда, значит время вышло, а новой сессии не появилось
    logger.info(f"Timeout reached for alias={alias}, phone={phone}. No new session found.")
    await bot.send_message(
        chat_id,
        f"Время ожидания (до {max_duration} сек.) истекло, новая сессия не появилась. "
        "Если вы не смогли авторизоваться, попробуйте заново.",
        parse_mode="HTML"
    )


async def listen_for_code_and_check_session(string_session: str, chat_id: int, alias: str, phone: str):
    """
    Подключается к Телеграму, слушает чат 777000 для перехвата кода
    и параллельно проверяет появление новых сессий через GetAuthorizationsRequest.

    :param string_session: Сохранённая авторизованная сессия
    :param chat_id: ID чата в Телеграм, куда отправлять сообщения пользователю
    :param alias: Alias аккаунта
    :param phone: Телефон аккаунта
    """
    client = TelegramClient(StringSession(string_session), API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    # Сколько сессий уже есть?
    try:
        auth_result = await client(GetAuthorizationsRequest())
        initial_count = len(auth_result.authorizations)
    except SessionRevokedError:
        # Сессия отозвана до того, как мы вообще начали
        logger.warning(f"Session revoked immediately for alias={alias}, phone={phone}")
        await bot.send_message(chat_id, f"Сессия аккаунта <b>{alias}</b> уже отозвана. Удаляем из БД.", parse_mode="HTML")
        delete_telegram_account(alias, phone)
        await client.disconnect()
        return
    except Exception as e:
        logger.exception(f"Failed to get authorizations for alias={alias}, phone={phone}: {e}")
        await bot.send_message(chat_id, f"Ошибка при получении списка сессий: {e}")
        await client.disconnect()
        return

    @client.on(events.NewMessage(incoming=True, chats=(777000,)))
    async def code_handler(event):
        """
        Перехватываем код из чата 777000 и пересылаем пользователю.
        """
        message_text = event.raw_text
        match = re.search(r"\b\d{5,6}\b", message_text)
        if match:
            code = match.group(0)
            logger.info(f"Code {code} received for alias={alias}, phone={phone}")
            await bot.send_message(
                chat_id,
                f"🔑 Ваш код подтверждения: <code>{code}</code>",
                parse_mode="HTML"
            )

    # Запускаем фоновый опрос сессий
    asyncio.create_task(poll_for_new_session(client, initial_count, alias, phone, chat_id))

    # Удерживаем подключение
    try:
        await client.run_until_disconnected()
    except SessionRevokedError:
        logger.warning(f"Session revoked while listening for code. alias={alias}, phone={phone}")
        await bot.send_message(chat_id, f"Сессия аккаунта <b>{alias}</b> была отозвана. Удаляем из БД.", parse_mode="HTML")
        delete_telegram_account(alias, phone)
        await client.disconnect()
    except Exception as e:
        logger.exception(f"Unhandled error in run_until_disconnected: {e}")
        await bot.send_message(chat_id, f"Неизвестная ошибка в прослушивании: {e}")
        await client.disconnect()


@router.message(Command("take_tg"))
async def cmd_take_tg(message: types.Message, current_user: User):
    """
    Выводит номер телефона, привязанный к аккаунту, и запускает фоновый процесс
    для прослушивания чата и проверки новых сессий.
    """
    alias = message.text.split(maxsplit=1)[1].strip() if len(message.text.split()) > 1 else None
    if not alias:
        await message.answer(
            "Введите alias аккаунта после команды. Пример: /take_tg <i>my_account</i>",
            parse_mode="HTML"
        )
        return

    account = get_telegram_account_by_alias(user_id=current_user.id, alias=alias)
    if not account:
        await message.answer("Аккаунт не найден, проверьте alias и попробуйте заново.")
        return

    # Выводим информацию об аккаунте
    if account.get('two_factor'):
        msg_text = (
            f"✅ Вот номер телефона, привязанный к аккаунту <b>{alias}</b>:\n"
            f"📞 <code>{account['phone']}</code>\n"
            f"pass: <code>{account['two_factor_pass']}</code>\n\n"
            "Введите этот номер в Telegram."
        )
    else:
        msg_text = (
            f"✅ Вот номер телефона, привязанный к аккаунту <code>{alias}</code>:\n"
            f"📞 <code>{account['phone']}</code>\n\n"
            "Введите этот номер в Telegram."
        )

    await message.answer(msg_text, parse_mode="HTML")

    # Запускаем фоновую задачу для прослушки кода и проверки новых сессий
    asyncio.create_task(
        listen_for_code_and_check_session(
            string_session=account['session_string'],
            chat_id=message.chat.id,
            alias=alias,
            phone=account['phone']
        )
    )
