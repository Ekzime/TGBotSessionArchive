from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

from bot.FSM.states import GiveTgStates

from db.services.telegram_crud import *
from dotenv import load_dotenv
import os

load_dotenv()  # загрузка переменных из .env
API_TELETHON_ID = int(os.getenv("API_TELETHON_ID"))
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
        # сохраняем промежуточные данные
        await state.update_data(
            phone=phone,
            session_string=client.session.save(),
            phone_code_hash=sent_code.phone_code_hash
        )
    except Exception as e:
        await message.answer(f"Ошибка при отправке кода: {e}")
        await client.disconnect()
        await state.clear()
        return
    await message.answer("Введите код из SMS/Telegram:")
    await state.set_state(GiveTgStates.wait_code)
    await client.disconnect()

@router.message(GiveTgStates.wait_code)
async def give_rg_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()

    # Восстанавливаем Telethon-клиент из session_string
    client = TelegramClient(StringSession(data["session_string"]), API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    # вход на аккаунт
    try:
        await client.sign_in(
            phone=data["phone"],
            code=code,
            phone_code_hash=data["phone_code_hash"]
        )
    except SessionPasswordNeededError:
        # Нужно 2FA
        await message.answer("Введите пароль 2FA:")
        await state.update_data(raw_session=client.session.save())
        await state.set_state(GiveTgStates.wait_2fa)
        await client.disconnect()
        return
    except Exception as e:
        await message.answer(f"Ошибка авторизации: {e}")
        await client.disconnect()
        await state.clear()
        return
    # Успешная авторизация без 2FA
    session_string = client.session.save()
    await client.disconnect()

    # Спросим alias (чтобы пользователь назвал аккаунт)
    await state.update_data(session_string=session_string)
    await message.answer("Введите alias (название аккаунта):")
    await state.set_state(GiveTgStates.wait_alias)

    await message.answer("Аккаунт успешно сдан!")

@router.message(GiveTgStates.wait_alias)
async def give_tg_alias(message: types.Message, state: FSMContext):
    alias = message.text.strip()
    data = await state.get_data()

    # Сохраним в БД
    try:
        create_telegram_account(
            user_id=message.from_user.id,  # или current_user.id, если AuthMiddleware
            alias=alias,
            phone=data["phone"],
            session_string=data["session_string"],
            two_factor=False,  # если дошли сюда без 2FA
        )
        await message.answer(f"Аккаунт '{alias}' успешно сохранён!")
    except Exception as e:
        await message.answer(f"Ошибка сохранения: {e}")

    await state.clear()

@router.message(GiveTgStates.wait_2fa)
async def give_tg_2fa(message: types.Message, state: FSMContext):
    password_2fa = message.text.strip()
    data = await state.get_data()

    client = TelegramClient(StringSession(data["raw_session"]), "API_ID", "API_HASH")
    await client.connect()

    try:
        await client.sign_in(password=password_2fa)
    except Exception as e:
        await message.answer(f"Ошибка 2FA: {e}")
        await client.disconnect()
        await state.clear()
        return
    session_string = client.session.save()
    await client.disconnect()

    # Спросим alias
    await state.update_data(session_string=session_string, two_factor_pass=password_2fa)
    await message.answer("Введите alias (название аккаунта):")
    await state.set_state(GiveTgStates.wait_alias_2fa)

@router.message(GiveTgStates.wait_alias_2fa)
async def give_tg_alias_2fa(message: types.Message, state: FSMContext):
    alias = message.text.strip()
    data = await state.get_data()

    try:
        create_telegram_account(
            user_id=message.from_user.id,
            alias=alias,
            phone=data["phone"],
            session_string=data["session_string"],
            two_factor=True,
            two_factor_pass=data["two_factor_pass"]  # если хочешь хранить 2FA
        )
        await message.answer(f"Аккаунт '{alias}' (с 2FA) успешно сохранён!")
    except Exception as e:
        await message.answer(f"Ошибка сохранения: {e}")

    await state.clear()