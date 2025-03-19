import asyncio
import re
import os

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.orm.sync import clear
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from bot.core.bot_instance import bot
from db.services.telegram_crud import get_telegram_account_by_alias
from db.models.model import User
from dotenv import load_dotenv

load_dotenv()
API_TELETHON_ID = int(os.getenv("API_TELETHON_ID"))
API_TELETHON_HASH = os.getenv("API_TELETHON_HASH")

router = Router()

async def listen_for_code(string_session, chat_id):
    """Функция для перехвата кода подтверждения и отправки его пользователю."""
    client = TelegramClient(StringSession(string_session), API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    # прослушка чата 777000
    @client.on(events.NewMessage(incoming=True, chats=(777000,)))
    async def handler(event):
        message_text = event.raw_text
        # Ищем числовой код из 5-6 цифр
        match = re.search(r"\b\d{5,6}\b", message_text)
        if match:
            code = match.group(0)
            await bot.send_message(chat_id, f"🔑 Ваш код подтверждения: {code}")
    # удержание подключения, для обработчика
    await client.run_until_disconnected()


@router.message(Command("take_tg"))
async def cmd_take_tg(message: types.Message, current_user: User):
    """Показываем список alias и ждём, какой выбрать."""
    alias = message.text.split(maxsplit=1)[1].strip() if len(message.text.split()) > 1 else None
    if not alias:
        await message.answer("Введите alias аккаунта после команды. Пример: `/give_tg <my_account>`")
        return

    # получение данных об аккаунте с БД
    account = get_telegram_account_by_alias(user_id=current_user.id, alias=alias)
    if not account:
        await message.answer("Аккаунт не найден, проверьте alias и попробуйте заново.")
        return

    # проверка на наличие f2a, для вывода пользователю
    if account.get('two_factor') is True:
        await message.answer(
            f"✅ Вот номер телефона, привязанный к аккаунту {alias}:\n📞 {account['phone']}\npass: {account['two_factor_pass']} \n\nВведите этот номер в Telegram.")
    else:
        await message.answer(f"✅ Вот номер телефона, привязанный к аккаунту {alias}:\n📞 {account['phone']}\n\nВведите этот номер в Telegram.")

    # Запускаем фонового слушателя кода
    asyncio.create_task(listen_for_code(account['session_string'], message.chat.id))