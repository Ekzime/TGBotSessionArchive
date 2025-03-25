from multiprocessing import Value
import uuid
import logging
from datetime import datetime, timedelta
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from db.models.model import User, UserSession
from db.services.manager import get_db_session

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def set_new_admin(username: str):
    with get_db_session() as db:
        new_admin = db.query(User).filter_by(username=username).first()
        if new_admin.is_admin is True:
            logger.info(
                f"set_new_admin: пользоватль {new_admin.username} уже имеет права администратора!"
            )
            return
        new_admin.is_admin = True
        logger.info(f"set_new_admin: Назначен новый админ: {new_admin.username}")


def create_admin_account(username: str, password: str, is_admin: bool = True):
    """
    Создает по умолчанию профиль с is_admin=True, для последующих манипулций с ботом через админку
    """
    with get_db_session() as db:
        current_admin = (
            db.query(User).filter_by(username=username, is_admin=True).first()
        )
        if current_admin:
            logger.info(
                f"Create_admin_account: Первинный админ уже существует! Username={username}"
            )
            return
        register_user(username=username, password=password, is_admin=is_admin)
        logger.info(f"Create_admin_account: Создан новый админ с username={username}")


def register_user(username: str, password: str, is_admin: bool = False) -> dict:
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
            raise ValueError(
                "Пароль не может быть меньше 4 символов! Введите /register, и попробуйте заново"
            )

        # хеширование пароля
        hash_password = bcrypt.hash(password)

        # создание нового юзера
        new_user = User(
            username=username, password_hash=hash_password, is_admin=is_admin
        )
        db.add(new_user)
        db.flush()  # чтобы new_user.id заполнилось
        # Формируем словарь
        user_data = {
            "id": new_user.id,
            "username": new_user.username,
            "is_admin": new_user.is_admin,
        }
        # Автоматический commit при выходе из with, если нет исключений
        return user_data


def login_user(
    username: str, password: str, telegram_user_id: int, session_hours=24
) -> dict:
    """
    Авторизует пользователя:
    - Проверяем, что пользователь существует
    - Сверяем пароль
    - Создаём сессию (запись в user_sessions)
    - Возвращаем session_token
    """
    with get_db_session() as db:
        # 1) Проверяем пользователя
        user: User = db.query(User).filter(User.username == username).first()  # type: ignore
        if not user:
            raise ValueError(
                "Пользователь не найден! Пройдите регистрацию для входа! \n Введите /register для регистрации профиля."
            )
        # 2) проверка пароля
        if not bcrypt.verify(password, user.password_hash):
            raise ValueError("Неверный пароль, введите /login и попробуйте еще раз!")

        # 3) Удаляем ВСЕ старые сессии:
        db.query(UserSession).filter(
            (UserSession.user_id == user.id)
            | (UserSession.telegram_user_id == str(telegram_user_id))
        ).delete(synchronize_session=False)

        # 4) Создаём новую сессию
        token = str(uuid.uuid4())
        expires = datetime.utcnow() + timedelta(hours=session_hours)
        new_session = UserSession(
            user_id=user.id,
            telegram_user_id=str(telegram_user_id),
            session_token=token,
            expires_at=expires,
        )
        db.add(new_session)
        # Используем flush(), чтобы получить new_session.id (и другие поля) до выхода из with
        db.flush()
        # Формируем словарь с нужными данными
        session_data = {
            "id": new_session.id,
            "session_token": new_session.session_token,
            "expires_at": new_session.expires_at,
            "user_id": user.id,
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


def get_current_user(db: Session, telegram_user_id: int):
    """
    Возвращает объект User, если у данного telegram_user_id есть активная сессия,
    иначе None.
    """
    session_obj = (
        db.query(UserSession).filter_by(telegram_user_id=str(telegram_user_id)).first()
    )
    if not session_obj:
        return None

    # проверка, истекла ли сессия
    if session_obj.expires_at < datetime.utcnow():
        # если истекла, удаляем и возврат None
        db.delete(session_obj)
        db.commit()
        return None

    return (
        session_obj.user
    )  # т.к. user = relationship("User", back_populates="sessions")
