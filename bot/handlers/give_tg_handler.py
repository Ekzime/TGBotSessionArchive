import os
# сторонние библиотеки
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
# локальные модули
from bot.FSM.states import GiveTgStates
from db.models.model import User
from db.services.telegram_crud import (
    create_telegram_account,
    get_telegram_account_by_phone,
    get_telegram_account_by_alias
)


load_dotenv()  # загрузка переменных из .env
API_TELETHON_ID = int(os.getenv("API_TELETHON_ID"))
API_TELETHON_HASH = os.getenv("API_TELETHON_HASH")
router = Router()


@router.message(Command("give_tg"))
async def cmd_give_tg(message: types.Message, state: FSMContext):
    await message.answer("<b>Введите номер телефона:</b>",parse_mode="HTML")
    await state.set_state(GiveTgStates.wait_phone)


@router.message(GiveTgStates.wait_phone)
async def give_tg_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    client = TelegramClient(StringSession(), API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    try:
        sent_code = await client.send_code_request(phone=phone)
        await state.update_data(
            phone=phone,
            session_string=client.session.save(),
            phone_code_hash=sent_code.phone_code_hash
        )
    except Exception as e:
        await message.answer(f"Ошибка при отправке кода! Введите /give_tg и отправьте корректный код из смс!")
        await client.disconnect()
        await state.clear()
        return

    await message.answer("<b>Введите код из SMS/Telegram:</b>",parse_mode="HTML")
    await state.set_state(GiveTgStates.wait_code)
    await client.disconnect()


@router.message(GiveTgStates.wait_code)
async def give_rg_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()

    client = TelegramClient(StringSession(data["session_string"]), API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    try:
        await client.sign_in(phone=data["phone"], code=code, phone_code_hash=data["phone_code_hash"])
        await message.answer("Бот успешно авторизован!")
    except SessionPasswordNeededError:
        await message.answer("Аккаунт защищен двухфакторной авторизацией. Введите пароль <b>2FA</b>:",parse_mode="HTML")
        await state.set_state(GiveTgStates.wait_2fa)
        await client.disconnect()
        return
    except Exception as e:
        await message.answer(f"Ошибка авторизации: {e}")
        await client.disconnect()
        await state.clear()
        return

    session_string = client.session.save()
    await client.disconnect()

    await state.update_data(session_string=session_string)
    await message.answer("Введите <b>alias</b> (название аккаунта) для сохранение в базе:",parse_mode="HTML")
    await state.set_state(GiveTgStates.wait_alias)


@router.message(GiveTgStates.wait_alias)
async def give_tg_alias(message: types.Message, state: FSMContext, current_user: User):
    alias = message.text.strip()
    data = await state.get_data()

    # проверяем существующий аккаунт по номеру телефона или alias
    existing_account = get_telegram_account_by_alias(current_user.id, alias)
    existing_account_by_phone = get_telegram_account_by_phone(current_user.id, data["phone"])

    if existing_account_by_phone:
        await message.answer(f"Аккаунт с номером телефона <code>{data['phone']}</code> уже сохранён ранее под alias <code>{existing_account_by_phone['alias']}</code>. Повторно сохранять его не нужно.",parse_mode="HTML")
        await state.clear()
        return

    if existing_account:
        await message.answer(f"Alias <code>{alias}</code> уже используется. Введите другой <b>alias</b>:",parse_mode="HTML")
        return  # Оставляем состояние неизменным, чтобы пользователь ввел новый alias

    # Сохраняем в БД, если всё ок.
    try:
        create_telegram_account(
            user_id=current_user.id,
            alias=alias,
            phone=data["phone"],
            session_string=data["session_string"],
            two_factor=False,
        )
        await message.answer(f"Аккаунт <code>{alias}</code> успешно сохранён!",parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка сохранения: {e}")

    await state.clear()


@router.message(GiveTgStates.wait_2fa)
async def give_tg_2fa(message: types.Message, state: FSMContext):
    password_2fa = message.text.strip()
    data = await state.get_data()

    client = TelegramClient(StringSession(data["session_string"]), API_TELETHON_ID, API_TELETHON_HASH)
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

    await state.update_data(session_string=session_string, two_factor_pass=password_2fa)
    await message.answer("Введите alias (название аккаунта):")
    await state.set_state(GiveTgStates.wait_alias_2fa)

@router.message(GiveTgStates.wait_alias_2fa)
async def give_tg_alias_2fa(message: types.Message, state: FSMContext, current_user: User):
    alias = message.text.strip()
    data = await state.get_data()

    existing_account = get_telegram_account_by_alias(current_user.id, alias)
    existing_account_by_phone = get_telegram_account_by_phone(current_user.id, data["phone"])

    if existing_account_by_phone:
        await message.answer(f"Аккаунт с номером телефона <code>{data['phone']}</code> уже сохранён ранее под alias <code>{existing_account_by_phone['alias']}</code>. Повторно сохранять его не нужно.",parse_mode="HTML")
        await state.clear()
        return

    if existing_account:
        await message.answer(f"Alias <code>{alias}</code> уже используется. Введите другой <b>alias</b>:",parse_mode="HTML")
        return  # Оставляем состояние неизменным

    # Сохраняем в БД
    try:
        create_telegram_account(
            user_id=current_user.id,
            alias=alias,
            phone=data["phone"],
            session_string=data["session_string"],
            two_factor=True,
            two_factor_pass=data["two_factor_pass"]
        )
        await message.answer(f"Аккаунт <code>{alias}</code> (с 2FA) успешно сохранён!",parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка сохранения: {e}")

    await state.clear()