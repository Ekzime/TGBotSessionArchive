from aiogram import BaseMiddleware # базовый класс для мидлварей Aiogram.
from typing import Callable, Awaitable, Dict, Any #  типы для аннотаций.
from aiogram.types import Message
from db.database import SessionLocal
from db.services.user_crud import get_current_user # функция, которая проверяет в БД, есть ли активная сессия для telegram_user_id, и возвращает объект User или None.

class AuthMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], # функция (хендлер), которую нужно вызвать, если всё ок.
            event: Message, # само событие
            data: Dict[str, Any] # словарь с данными, который передаётся по цепочке
    ) -> Any:
        db = SessionLocal() # создаём новую сессию к БД (SQLAlchemy
        user = None #  по умолчанию считаем, что «пользователь не залогинен»
        if event.from_user: # проверяем, есть ли отправитель у сообщения
            # Пытаемся найти текущего пользователя
            from_user_id = event.from_user.id
            user = get_current_user(db, from_user_id)

        # Кладём результат в data["current_user"]
        data["current_user"] = user

        try:
            result = await handler(event,data)
        finally:
            db.close()