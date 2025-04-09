import logging
import re

# сторонние библиотеки
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    SessionRevokedError,
    FloodWaitError,
)
from telethon.sessions import StringSession
from telethon import functions

# локальные модули
from config import settings
from bot.FSM.states import GiveTgStates
from db.models.model import User
from db.services.telegram_crud import (
    create_telegram_account,
    get_telegram_account_by_phone,
    get_telegram_account_by_alias,
    update_telegram_account,
)

API_TELETHON_ID = settings.API_TELETHON_ID
API_TELETHON_HASH = settings.API_TELETHON_HASH

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = Router()


def _normalize_phone(phone: str):
    phone = phone.strip().replace(" ", "")

    if not phone.startswith("+"):
        phone = "+" + phone
    if re.fullmatch(r"\+\d{10,15}", phone):
        return phone
    else:
        raise ValueError(
            "Некорректный формат номера телефона. Он должен начинаться с '+' и содержать от 10 до 15 цифр."
        )


@router.message(Command("give_tg"))
async def cmd_give_tg(message: types.Message, state: FSMContext):
    """
    Хендлер, который запускает процесс передачи аккаунта:
    1) Запрашивает номер телефона.
    """
    await message.answer("<b>Введите номер телефона:</b>", parse_mode="HTML")
    await state.set_state(GiveTgStates.wait_phone)


@router.message(GiveTgStates.wait_phone)
async def give_tg_phone(message: types.Message, state: FSMContext):
    """
    Хендлер, принимающий номер телефона и отправляющий код на этот номер.
    """
    phone = message.text.strip()
    try:
        phone = _normalize_phone(phone=phone)
    except ValueError as e:
        await message.answer(
            f"Ошибка: {e}\nВведите номер в корректном формате (например, +12345678901):"
        )
        return
    client = TelegramClient(StringSession(), API_TELETHON_ID, API_TELETHON_HASH)
    await client.connect()

    try:
        sent_code = await client.send_code_request(phone=phone)
        # Сохраняем данные в FSM
        await state.update_data(
            phone=phone,
            session_string=client.session.save(),
            phone_code_hash=sent_code.phone_code_hash,
        )
        await message.answer("<b>Введите код из SMS/Telegram:</b>", parse_mode="HTML")
        await state.set_state(GiveTgStates.wait_code)

    except FloodWaitError as e:
        logger.warning(
            f"FloodWaitError при отправке кода: нужно подождать {e.seconds} сек."
        )
        await message.answer(
            f"Слишком много запросов. Подождите {e.seconds} секунд и попробуйте снова."
        )
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка при отправке кода на номер {phone}: {e}")
        await message.answer(
            "Ошибка при отправке кода! Проверьте номер телефона или попробуйте позже.\n\n"
            "Для повторной попытки введите /give_tg"
        )
        await state.clear()
    finally:
        await client.disconnect()


@router.message(GiveTgStates.wait_code)
async def give_tg_code(message: types.Message, state: FSMContext):
    """
    Хендлер, принимающий код подтверждения и пытающийся авторизовать аккаунт.
    """
    code = message.text.strip()
    # проверка на то, что ввели только integer, длина кода 5
    if not code.isdigit() or len(code) not in (5, 6):
        data = await state.get_data()
        attempts = data.get("code_attempts", 0) + 1
        await state.update_data(code_attempts=attempts)
        # если количество попыток больше 3, сброс состояния
        if attempts >= 3:
            await message.answer(
                "❗ Превышено количество попыток ввода кода.\n"
                "Начните процесс заново командой /give_tg."
            )
            await state.clear()
            return

        await message.answer(
            f"❗ Неверный формат кода ({attempts}/3). Попробуйте ещё раз:"
        )
        return

    data = await state.get_data()

    client = TelegramClient(
        StringSession(data["session_string"]), API_TELETHON_ID, API_TELETHON_HASH
    )
    await client.connect()

    try:
        await client.sign_in(
            phone=data["phone"], code=code, phone_code_hash=data["phone_code_hash"]
        )

        try:
            await client(functions.account.ResetAuthorizationRequest(hash=0))
        except Exception as e:
            logger.error(f"give_tg_code: не удалось кикнуть остальные сессии: {e}")

        await message.answer(
            "✅ <b>Аккаунт успешно авторизован. Другие сессии были отозваны.</b>",
            parse_mode="HTML",
        )

        # Сохраняем актуальную сессию
        session_string = client.session.save()
        await state.update_data(session_string=session_string)

        # Переходим к запросу alias
        await message.answer(
            "Введите <b>alias</b> (название аккаунта) для сохранения в базе:",
            parse_mode="HTML",
        )
        await state.set_state(GiveTgStates.wait_alias)

    except SessionPasswordNeededError:
        logger.info(f"Аккаунт {data['phone']} защищен 2FA.")
        await message.answer(
            "Аккаунт защищён двухфакторной авторизацией.\n"
            "Введите пароль <b>2FA</b>:",
            parse_mode="HTML",
        )
        await state.set_state(GiveTgStates.wait_2fa)
    except SessionRevokedError:
        logger.warning(f"Сессия отозвана пользователем (номер {data['phone']}).")
        await message.answer(
            "Сессия отозвана пользователем. Повторите процесс заново командой /give_tg."
        )
        await state.clear()
    except FloodWaitError as e:
        logger.warning(
            f"FloodWaitError при авторизации: нужно подождать {e.seconds} сек."
        )
        await message.answer(
            f"Слишком много попыток ввода кода. Подождите {e.seconds} секунд и попробуйте снова."
        )
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка авторизации (номер {data['phone']}): {e}")
        # Проверяем, не истёк ли код
        if "confirmation code has expired" in str(e).lower():
            await message.answer(
                "❗ Код подтверждения истек. Повторите процесс заново командой /give_tg."
            )
        else:
            await message.answer(f"Ошибка авторизации: {e}")
        await state.clear()
    finally:
        await client.disconnect()


@router.message(GiveTgStates.wait_alias)
async def give_tg_alias(message: types.Message, state: FSMContext, current_user: User):
    """
    Хендлер, принимающий alias (без 2FA).
    Сохраняет данные об аккаунте в БД.
    Если аккаунт с тем же номером телефона уже существует, обновляет флаг is_taken на False.
    """
    alias = message.text.strip()
    data = await state.get_data()

    # Проверяем, есть ли аккаунт по номеру телефона для данного пользователя
    existing_account_by_phone = get_telegram_account_by_phone(
        current_user.id, data["phone"]
    )
    if existing_account_by_phone:
        # Обновляем существующий аккаунт, снимая флаг is_taken (делаем аккаунт "свободным")
        update_telegram_account(existing_account_by_phone, alias=alias, is_taken=False)
        await message.answer(
            f"Аккаунт с номером телефона <code>{data['phone']}</code> сохранен.\n",
            f"под alias <code>{existing_account_by_phone['alias']}</code>.\n\n",
            parse_mode="HTML",
        )
        await state.clear()
        return

    # Проверяем, не используется ли уже введённый alias для данного пользователя
    existing_account = get_telegram_account_by_alias(current_user.id, alias)
    if existing_account:
        await message.answer(
            f"Alias <code>{alias}</code> уже используется.\n"
            "Введите другой <b>alias</b>:",
            parse_mode="HTML",
        )
        return  # Не очищаем состояние, ждём новое значение alias

    try:
        create_telegram_account(
            user_id=current_user.id,
            alias=alias,
            phone=data["phone"],
            session_string=data["session_string"],
            two_factor=False,
        )
        await message.answer(
            f"Аккаунт <code>{alias}</code> успешно сохранён!", parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Ошибка сохранения аккаунта {alias}: {e}")
        await message.answer(f"Ошибка сохранения: {e}")

    await state.clear()


@router.message(GiveTgStates.wait_2fa)
async def give_tg_2fa(message: types.Message, state: FSMContext):
    """
    Хендлер, принимающий пароль 2FA, если включена двухфакторная аутентификация.
    """
    password_2fa = message.text.strip()
    data = await state.get_data()

    client = TelegramClient(
        StringSession(data["session_string"]), API_TELETHON_ID, API_TELETHON_HASH
    )
    await client.connect()

    try:
        await client.sign_in(password=password_2fa)
        # Сохраняем обновлённую сессию
        session_string = client.session.save()
        await state.update_data(
            session_string=session_string, two_factor_pass=password_2fa
        )

        await message.answer(
            "Введите <b>alias</b> (название аккаунта) для сохранения:",
            parse_mode="HTML",
        )
        await state.set_state(GiveTgStates.wait_alias_2fa)

    except SessionRevokedError:
        logger.warning(f"Сессия отозвана во время ввода 2FA (номер {data['phone']}).")
        await message.answer("Сессия отозвана. Повторите процесс заново /give_tg.")
        await state.clear()
    except FloodWaitError as e:
        logger.warning(f"FloodWaitError при вводе 2FA: {e.seconds} сек.")
        await message.answer(
            f"Слишком много попыток. Подождите {e.seconds} секунд и попробуйте снова."
        )
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка 2FA (номер {data['phone']}): {e}")
        await message.answer(f"Ошибка 2FA: {e}")
        await state.clear()
    finally:
        await client.disconnect()


@router.message(GiveTgStates.wait_alias_2fa)
async def give_tg_alias_2fa(
    message: types.Message, state: FSMContext, current_user: User
):
    """
    Хендлер, принимающий alias при 2FA-аккаунте и сохраняющий в БД.
    """
    alias = message.text.strip()
    data = await state.get_data()

    # Проверяем, есть ли аккаунт по номеру телефона для данного пользователя
    existing_account_by_phone = get_telegram_account_by_phone(
        current_user.id, data["phone"]
    )

    if existing_account_by_phone:
        # Обновляем существующий аккаунт, снимая флаг is_taken (делаем аккаунт "свободным")
        update_telegram_account(existing_account_by_phone, alias=alias, is_taken=False)
        await message.answer(
            f"Аккаунт с номером телефона <code>{data['phone']}</code> сохранен.\n"
            f"под alias <code>{alias}</code>.\n\n",
            parse_mode="HTML",
        )
        await state.clear()
        return

    # Проверяем, не используется ли уже введённый alias для данного пользователя
    existing_account = get_telegram_account_by_alias(current_user.id, alias)
    if existing_account:
        await message.answer(
            f"Alias <code>{alias}</code> уже используется.\n"
            "Введите другой <b>alias</b>:",
            parse_mode="HTML",
        )
        return  # Не очищаем состояние, ждём новое значение alias

    try:
        create_telegram_account(
            user_id=current_user.id,
            alias=alias,
            phone=data["phone"],
            session_string=data["session_string"],
            two_factor=True,
            two_factor_pass=data["two_factor_pass"],
            is_monitoring=True,
            is_taken=False,
        )
        await message.answer(
            f"Аккаунт <code>{alias}</code> (с 2FA) успешно сохранён!", parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Ошибка сохранения 2FA-аккаунта {alias}: {e}")
        await message.answer(f"Ошибка сохранения: {e}")

    await state.clear()
