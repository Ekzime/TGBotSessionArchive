import uuid
from passlib.hash import bcrypt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, raiseload

from db.models.model import User, UserSession
from db.services.manager import get_db_session # контекст менеджер

def register_user(username: str,password: str, is_admin: bool=False) -> User:
    """
        Регистрирует нового пользователя:
        - Проверяет, что username не занят
        - Хеширует пароль
        - Создаёт запись в таблице users
    """
    with get_db_session() as db:
        # проверка, нет ли такого пользователя в БД
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError("Пользователь с таким именем уже существует!")

        # проверка на длину пароля
        if len(password) < 4:
            raise ValueError("Пароль не может быть меньше 4 символов! Введите /register, и попробуйте заново")

        # хеширование пароля
        hash_password = bcrypt.hash(password)

        # создание нового юзера
        new_user = User(
            username=username,
            password_hash=hash_password,
            is_admin=is_admin
        )
        db.add(new_user)
        db.flush()  # чтобы new_user.id заполнилось
        # Формируем словарь
        user_data = {
            "id": new_user.id,
            "username": new_user.username,
            "is_admin": new_user.is_admin
        }
        # Автоматический commit при выходе из with, если нет исключений
        return user_data

def login_user(username: str, password: str, telegram_user_id: int, session_hours=24) -> UserSession:
    """
        Авторизует пользователя:
        - Проверяем, что пользователь существует
        - Сверяем пароль
        - Создаём сессию (запись в user_sessions)
        - Возвращаем session_token
    """
    with get_db_session() as db:
        # 1) Проверяем пользователя
        user = db.query(User).filter(User.username == username).first()  # type: ignore
        if not user:
            raise ValueError(
                "Пользователь не найден! Пройдите регистрацию для входа! \n Введите /register для регистрации профиля.")
        # 2) проверка пароля
        if not bcrypt.verify(password, user.password_hash):
            raise ValueError("Неверный пароль, введите /login и попробуйте еще раз!")

        # 3) Проверяем, нет ли уже сессии
        existing_session = db.query(UserSession).filter_by(telegram_user_id=str(telegram_user_id)).first()
        if existing_session:
            # здесь так и не определился. Если есть текущая сессия, ее можно удалить и создать новую, либо выбросить исключение
            # db.delete(existing_session)
            # db.commit()
            raise ValueError("У вас уже есть активная сессия! Что бы выйти, введите /logout")

        # 4) Создаём новую сессию
        token = str(uuid.uuid4())
        expires = datetime.utcnow() + timedelta(hours=session_hours)
        new_session = UserSession(
            user_id=user.id,
            telegram_user_id=str(telegram_user_id),
            session_token=token,
            expires_at=expires
        )
        db.add(new_session)
        # Используем flush(), чтобы получить new_session.id (и другие поля) до выхода из with
        db.flush()
        # Формируем словарь с нужными данными
        session_data = {
            "id": new_session.id,
            "session_token": new_session.session_token,
            "expires_at": new_session.expires_at,
            "user_id": user.id
        }
        # По выходу из блока with будет auto-commit (если нет исключений)
        return session_data



def logout_user(telegram_user_id: int):
    """
        Удаляет (или помечает неактивной) запись сессии по telegram_user_id
    """
    with get_db_session() as db:
        session_obj = db.query(UserSession).filter_by(telegram_user_id=str(telegram_user_id)).first()  # type: ignore
        if not session_obj:
            raise ValueError("Нет активной сессии")
        db.delete(session_obj)
        db.commit()

def get_current_user(db: Session,telegram_user_id: int):
    """
        Возвращает объект User, если у данного telegram_user_id есть активная сессия,
        иначе None.
    """
    session_obj = db.query(UserSession).filter_by(telegram_user_id=str(telegram_user_id)).first()
    if not session_obj:
        return None

    # проверка, истекла ли сессия
    if session_obj.expires_at < datetime.utcnow():
        # если истекла, удаляем и возврат None
        db.delete(session_obj)
        db.commit()
        return None

    return session_obj.user  # т.к. user = relationship("User", back_populates="sessions")