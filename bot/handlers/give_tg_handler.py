from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

from bot.FSM.states import GiveTgStates

from db.services.telegram_crud import (
    list_telegram_accounts, create_telegram_account, get_telegram_account_by_alias,
    update_telegram_account, decrypt_two_factor_pass
)

from dotenv import load_dotenv
import os

load_dotenv()  # загрузка переменных из .env
API_TELETHON_ID = os.getenv("API_TELETHON_ID")
API_TELETHON_HASH = os.getenv("API_TELETHON_HASH")
router = Router()

@router.message(Command("give_tg"))
async def cmd_give_tg(message: types.Message, state:FSMContext):
    await message.answer("Введите номер телефона: ")
    await state.set_state(GiveTgStates.wait_phone)

@router.message(GiveTgStates.wait_phone)
async def give_tg_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()

    # создаем telethon клиент в памяти
    client = TelegramClient(StringSession(),API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    # отправка кода
    try:
        sent_code = await client.send_code_request(phone=phone)
    except Exception as e:
        await message.answer(f"Ошибка при отправке кода: {e}")
        client.disconnect()
        await state.clear()
    # Сохраняем данные (phone, client.session.save(), phone_code_hash)
    await state.update_data(
        phone=phone,
        session_string=client.session.save(),
        phone_code_hash=sent_code.phone_code_hash # type: ignore
    )
    await message.answer("Введите код из Telegram/sms")
    await state.set_state(TgStates.wait_for_code)

@router.message(TgStates.wait_for_code)
async def give_rg_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    data = state.get_data()

    # Восстанавливаем Telethon-клиент из session_string
    client = TelegramClient(StringSession(data["session_string"]), API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    # вход на аккаунт
    try:
        await client.sign_in(
            phone=data['phone'],
            code=code,
            phone_code_hash=data["phone_code_hash"]
        )
    except SessionPasswordNeededError:
        # Нужно 2FA
        await message.answer("Требуется F2A(Облачный пароль)!")
        await state.update_data(raw_session=client.session.save()) # сохраним новую сессию
        await client.disconnect()
        await state.set_state(TgStates.wait_for_f2a)
    except Exception as e:
        await message.answer(f"Ошибка входа: {e}")
        await client.disconnect()
        await state.clear()
        return
    # Если дошли сюда — авторизация без 2FA успешна
    session_string = client.session.save()
    await client.disconnect()

    # cохраняем в бд
    await save_telegram_session_to_db(
        user_id=message.from_user.id,
        phone=data['phone'],
        session_string=session_string,
        two_factor=False
    )
    await message.answer("Аккаунт успешно сдан!")

