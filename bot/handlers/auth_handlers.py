from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.FSM.states import AuthStates

from db.database import SessionLocal
from db.services.user_crud import login_user, logout_user, register_user
from db.models.model import User

router = Router()


# ------------------- REGISTRATION -------------------
@router.message(Command("register"))
async def cmd_register(
    message: types.Message, state: FSMContext, current_user: User = None
):
    if current_user is not None:
        await message.answer(
            "Вы уже зарегистрированы и авторизованы!\nСначала сделайте /logout."
        )
        return
    await message.answer("<b>Введите username:</b> ", parse_mode="HTML")
    await state.set_state(AuthStates.wait_for_username)


@router.message(AuthStates.wait_for_username)
async def get_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    # сохранение имени во временном хранилище FSM
    await state.update_data(username=username)

    # Запрашиваем пароль, и переводим в другое состояние
    await message.answer(
        "<b>Введите пароль(Не менее 4 символов):</b> ", parse_mode="HTML"
    )
    await state.set_state(AuthStates.wait_for_pass)


@router.message(AuthStates.wait_for_pass)
async def get_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    if len(password) < 4:
        await message.answer(
            "<b>Короткий пароль! Введите заново:</b>", parse_mode="HTML"
        )
        return
    # сохраняем во временном хранилище FSM
    await state.update_data(password=password)

    # Если дабавлять подтверждение пароля, то тут
    data = await state.get_data()
    username = data["username"]

    # записываем в БД
    db = SessionLocal()
    try:
        user = register_user(username=username, password=password, is_admin=False)
        await message.answer(
            f"Регистрация прошла успешно!\n Что бы продолжить работу с ботом, войдите в профиль /login"
        )
    except ValueError as ve:
        # Ловим ValueError, который выходит при существующем пользователя
        await message.answer(
            f"Ошибка регистрации: Пользователь уже существует! \n Введите /login для входа!"
        )
    except Exception as e:
        # Ловим все остальные непредвиденные ошибки
        await message.answer(f"Произошла непредвиденная ошибка: {e}")
    finally:
        db.close()
    # очищаем состояние
    await state.clear()


# ------------------- LOGIN -------------------
@router.message(Command("login"))
async def cmd_login(
    message: types.Message, state: FSMContext, current_user: User = None
):
    if current_user is not None:
        await message.answer(
            "Вы уже зарегистрированы и авторизованы!\nСначала сделайте /logout."
        )
        return

    await message.answer("<b>Для авторизации введите username:</b> ", parse_mode="HTML")
    await state.set_state(AuthStates.wait_for_login_username)


@router.message(AuthStates.wait_for_login_username)
async def login_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    await state.update_data(username=username)

    await message.answer("<b>Введите пароль: </b>", parse_mode="HTML")
    await state.set_state(AuthStates.wait_for_login_password)


@router.message(AuthStates.wait_for_login_password)
async def login_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()  # получаем данные из временного хранилища
    username = data["username"]

    db = SessionLocal()
    try:
        session_obj = login_user(
            username, password, telegram_user_id=message.from_user.id
        )
        await message.answer(
            f"Вы успешно вошли в аккаунт! Нажмите /start для ознакомления."
        )
    except ValueError as e:
        await message.answer(f"Ошибка авторизации: {e}")
    except Exception as e:
        await message.answer(f"Неожиданная ошибка при входе: {e}")
    finally:
        db.close()
    await state.clear()  # Диалог закончен — сбрасываем состояние


# ------------------- LOGOUT -------------------
@router.message(Command("logout"))
async def cmd_logout(message: types.Message):
    db = SessionLocal()
    try:
        logout_user(telegram_user_id=message.from_user.id)
        await message.answer("Вы успешно разлогинились!")
    except ValueError as e:
        await message.answer(f"Ошибка логаута: {e}")
    finally:
        db.close()
