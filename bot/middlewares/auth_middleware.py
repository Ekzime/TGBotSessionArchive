from aiogram import BaseMiddleware # базовый класс для мидлварей Aiogram.
from typing import Callable, Awaitable, Dict, Any #  типы для аннотаций.
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from db.database import SessionLocal
from db.services.user_crud import get_current_user # функция, которая проверяет в БД, есть ли активная сессия для telegram_user_id, и возвращает объект User или None.
from bot.FSM.states import AuthStates

allowed_states = [
    AuthStates.wait_for_username,
    AuthStates.wait_for_pass,
    AuthStates.wait_for_pass_confirm,
    AuthStates.wait_for_login_username,
    AuthStates.wait_for_login_password
]
allowed_commands = ["/start", "/login", "/register"]


class CurrentUserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        # 1) Создаём новую сессию SQLAlchemy
        db = SessionLocal() # создаём новую сессию к БД (SQLAlchemy ORM)
        user = None #  по умолчанию считаем, что «пользователь не залогинен»
        # проверяем, есть ли отправитель у сообщения
        if event.from_user:
            from_user_id = event.from_user.id
            user = get_current_user(db, from_user_id) # Пытаемся найти текущего пользователя

        data["current_user"] = user # Кладём результат в data["current_user"]

        try:
            result = await handler(event,data)
        finally:
            db.close()

class AuthMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        db = SessionLocal()
        current_user = None

        try:
            if event.from_user:
                current_user = get_current_user(db, event.from_user.id)

            data["current_user"] = current_user

            state: FSMContext = data.get("state")
            current_state = await state.get_state() if state else None

            if current_user is None:
                command = event.text.split()[0] if event.text else ""

                if command not in allowed_commands and current_state not in allowed_states:
                    await event.answer("Сначала /login или /register, чтобы пользоваться ботом!")
                    return

            return await handler(event, data)

        finally:
            db.close()