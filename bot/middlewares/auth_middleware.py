from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.FSM.states import AuthStates

from db.database import SessionLocal
from db.services.user_crud import get_current_user

allowed_states = [
    AuthStates.wait_for_username,
    AuthStates.wait_for_pass,
    AuthStates.wait_for_pass_confirm,
    AuthStates.wait_for_login_username,
    AuthStates.wait_for_login_password
]
allowed_commands = ["/start", "/login", "/register"]

class AuthMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        # Создание новой сессии с базой данных при каждом запросе
        db = SessionLocal()
        current_user = None

        try:
            # Проверка, пришло ли событие от пользователя
            if event.from_user:
                current_user = get_current_user(db, event.from_user.id)

            # Добавляем текущего пользователя (или None) в словарь data,
            # чтобы он был доступен в дальнейшем внутри обработчиков
            data["current_user"] = current_user

            # Получаем текущее состояние FSM, если оно есть
            state: FSMContext = data.get("state")
            current_state = await state.get_state() if state else None

            # Если текущий пользователь не авторизован
            if current_user is None:
                # Извлекаем команду (например: "/start", "/help", "/login")
                command = event.text.split()[0] if event.text else ""

                # Проверяем, является ли команда разрешённой для неавторизованных пользователей
                # либо состояние находится в списке разрешённых состояний
                if command not in allowed_commands and current_state not in allowed_states:
                    await event.answer("Сначала /login или /register, чтобы пользоваться ботом!")
                    return

            return await handler(event, data)

        finally:
            db.close()