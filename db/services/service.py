import uuid
from passlib.hash import bcrypt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, raiseload

from db.models.model import User, UserSession
from db.services.manager import get_db_session # контекст менеджер

def register_user(db: Session,username: str,password: str, is_admin: bool=False) -> User:
    """
        Регистрирует нового пользователя:
        - Проверяет, что username не занят
        - Хеширует пароль
        - Создаёт запись в таблице users
    """
    with get_db_session() as db:
        # проверка, нет ли такого пользователя в БД
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
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
        # коммит делает контекст менеджер!
        db.flush()
        db.refresh(new_user)
        # В конце блока `with` автоматически будет:
        # - commit() (если не было исключений)
        # - rollback() (если было исключение)
        # - close() (всегда)
        return new_user

def login_user(db: Session, username: str, password: str, telegram_user_id: int, session_hours=24) -> UserSession:
    """
        Авторизует пользователя:
        - Проверяем, что пользователь существует
        - Сверяем пароль
        - Создаём сессию (запись в user_sessions)
        - Возвращаем session_token
    """
    # проверка на существование юзера в таблицe
    user = db.query(User).filter(User.username==username).first() # type: ignore
    if not user:
        raise ValueError("Пользователь не найден! Пройдите регистрацию для входа! \n Введите /register для регистрации профиля.")
    # проверка пароля
    if not bcrypt.verify(password, user.password_hash):
        raise ValueError("Неверный пароль, введите /login и попробуйте еще раз!")

    # Проверка на существование сесии по telegram_user_id
    existing_session = db.query(UserSession).filter_by(telegram_user_id=str(telegram_user_id)).first()
    if existing_session:
        # здесь так и не определился. Если есть текущая сессия, ее можно удалить и создать новую, либо выбросить исключение
        # db.delete(existing_session)
        # db.commit()
        raise ValueError("У вас уже есть активная сессия! Что бы выйти, введите /logout")

    # создание сессии
    token = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(hours=session_hours)
    new_session = UserSession(
        user_id=user.id,
        session_token = token,
        expires_at = expires
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

def logout_user(db: Session, telegram_user_id: int):
    """
        Удаляет (или помечает неактивной) запись сессии по telegram_user_id
    """
    session_obj = db.query(UserSession).filter_by(telegram_user_id=str(telegram_user_id)).first() # type: ignore
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