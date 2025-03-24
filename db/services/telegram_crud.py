import logging
from datetime import datetime
from typing import List, Optional

from db.models.model import TelegramAccount, TelegramMessage, UserSession
from db.services.manager import get_db_session
from bot.utils.crypto import encrypt_text, decrypt_text

logger = logging.getLogger(__name__)


def _decrypt_two_factor_pass(two_factor_pass: str):
    return decrypt_text(two_factor_pass) if two_factor_pass else None


def _encrypt_two_factor_pass(two_factor_pass: str):
    return encrypt_text(two_factor_pass) if two_factor_pass else None


# ---------- TelegramMessage CRUD ----------


def create_telegram_message(
    account_id: int,
    chat_id: int,
    message_id: int,
    sender_id: Optional[int],
    text: str,
    date: datetime,
    logs_msg_id: Optional[int] = None,
    media_type: Optional[str] = None,
) -> dict:
    """
    Сохраняет новое сообщение в таблицу telegram_messages.
    Возвращает словарь с данными о сообщении.
    """
    with get_db_session() as db:
        msg = TelegramMessage(
            account_id=account_id,
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            text=text,
            date=date,
            logs_msg_id=logs_msg_id,
            media_type=media_type,
        )

        try:
            db.add(msg)
            db.commit()
            db.refresh(msg)
            logger.info(
                f"Создано сообщение id={msg.id}, chat_id={chat_id}, message_id={message_id}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при создании сообщения: {e}")
            raise e

        return {
            "id": msg.id,
            "account_id": msg.account_id,
            "chat_id": msg.chat_id,
            "message_id": msg.message_id,
            "sender_id": msg.sender_id,
            "text": msg.text,
            "date": msg.date,
            "deleted_at": msg.deleted_at,
            "logs_msg_id": msg.logs_msg_id,
            "media_type": msg.media_type,
            "created_at": msg.created_at,
            "updated_at": msg.updated_at,
        }


def mark_deleted_messages(account_id: int, message_ids: List[int]) -> None:
    """
    Помечает список сообщений (message_ids) как удалённые (deleted_at = now()).
    Если сообщение уже помечено, повторно не обновляет.
    """
    with get_db_session() as db:
        try:
            for msg_id in message_ids:
                row = (
                    db.query(TelegramMessage)
                    .filter_by(account_id=account_id, message_id=msg_id)
                    .first()
                )

                if row and row.deleted_at is None:
                    row.deleted_at = datetime.utcnow()

            db.commit()
            logger.info(
                f"Помечены удалёнными сообщения: {message_ids} для account_id={account_id}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при пометке удалённых: {e}")
            raise e


def list_messages_by_chat(
    account_id: int, chat_id: int, limit: int = 20, offset: int = 0
) -> list:
    """
    Возвращает список сообщений по заданному chat_id (и account_id),
    в порядке убывания по дате (последние сообщения в начале).
    Можно использовать limit/offset для пагинации.
    """
    with get_db_session() as db:
        query = (
            db.query(TelegramMessage)
            .filter_by(account_id=account_id, chat_id=chat_id)
            .order_by(TelegramMessage.date.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        rows = query.all()

        result = []
        for r in rows:
            result.append(
                {
                    "id": r.id,
                    "account_id": r.account_id,
                    "chat_id": r.chat_id,
                    "message_id": r.message_id,
                    "sender_id": r.sender_id,
                    "text": r.text,
                    "date": r.date,
                    "deleted_at": r.deleted_at,
                    "logs_msg_id": r.logs_msg_id,
                    "media_type": r.media_type,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
            )

        return result


# ---------- TelegramAccount CRUD ----------


def list_telegram_accounts_with_monitoring():
    """
    Возвращает список аккаунтов, у которых is_monitoring=True (для прослушки).
    """
    with get_db_session() as db:
        accounts = db.query(TelegramAccount).filter_by(is_monitoring=True).all()
        result = []
        for acc in accounts:
            result.append(
                {
                    "id": acc.id,
                    "alias": acc.alias,
                    "phone": acc.phone,
                    "session_string": acc.session_string,
                    "two_factor": acc.two_factor,
                    "two_factor_pass": _decrypt_two_factor_pass(acc.two_factor_pass),
                    "is_monitoring": acc.is_monitoring,
                    "is_taken": acc.is_taken,
                }
            )
        return result


def create_telegram_account(
    user_id: int,
    alias: str,
    phone: str,
    session_string: str = None,
    two_factor: bool = False,
    two_factor_pass: str = None,
):
    """
    Создаёт запись в telegram_accounts с проверками и обработкой ошибок.
    """
    with get_db_session() as db:
        if not user_id or not alias or not phone:
            raise ValueError("user_id, alias, and phone are required fields")

        existing_account = (
            db.query(TelegramAccount)
            .filter((TelegramAccount.phone == phone) | (TelegramAccount.alias == alias))
            .first()
        )
        if existing_account:
            raise ValueError(
                f"Телеграм аккаунт '{phone}' или элиас '{alias}' уже существует!"
            )

        account = TelegramAccount(
            user_id=user_id,
            alias=alias,
            phone=phone,
            session_string=session_string,
            two_factor=two_factor,
            two_factor_pass=_encrypt_two_factor_pass(two_factor_pass),
        )

        try:
            db.add(account)
            db.commit()
            db.refresh(account)
            logger.info(f"Телеграм аккаунт успешно сохранён: {account.id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка сохранения аккаунта: {e}")
            raise e

        return account


def get_telegram_account_by_telgram_id(telegram_user_id: int):
    """
    Ищет в таблице user_sessions запись, где telegram_user_id = <значение из Telegram>.
    Возвращает связанный объект User или None, если не найден.
    """
    with get_db_session() as db:
        session_obj = db.query(UserSession).filter_by(telegram_user_id=telegram_user_id).first()

        if not session_obj or not session_obj.user:
            return None

        user_obj = session_obj.user
        return {
            "id": user_obj.id,
            "username": user_obj.username,
            "password_hash": user_obj.password_hash,
            "is_admin": user_obj.is_admin,
            "created_at": user_obj.created_at,
            "updated_at": user_obj.updated_at
        }

def get_telegram_account_by_phone(user_id: int, phone: str):
    """
    Находит TelegramAccount по user_id & phone, используя таблицу telegram_accounts.
    Если аккаунт не найден, возвращает None.
    """
    with get_db_session() as db:
        account = (
            db.query(TelegramAccount).filter_by(user_id=user_id, phone=phone).first()
        )
        if account:
            return {
                "id": account.id,
                "alias": account.alias,
                "phone": account.phone,
                "session_string": account.session_string,
                "two_factor": account.two_factor,
                "two_factor_pass": _decrypt_two_factor_pass(account.two_factor_pass),
                "is_monitoring": account.is_monitoring,
                "is_taken": account.is_taken,
                "created_at": account.created_at,
                "updated_at": account.updated_at,
            }
        return None


def get_telegram_account_by_alias(user_id: int, alias: str):
    """
    Возвращает одну запись TelegramAccount (или None) по alias и user_id.
    """
    with get_db_session() as db:
        account = (
            db.query(TelegramAccount).filter_by(user_id=user_id, alias=alias).first()
        )
        if account:
            return {
                "id": account.id,
                "alias": account.alias,
                "phone": account.phone,
                "session_string": account.session_string,
                "two_factor": account.two_factor,
                "two_factor_pass": _decrypt_two_factor_pass(account.two_factor_pass),
                "is_monitoring": account.is_monitoring,
                "is_taken": account.is_taken,
                "created_at": account.created_at,
                "updated_at": account.updated_at,
            }
        return None


def list_telegram_accounts(user_id: int):
    """
    Возвращает список всех аккаунтов, принадлежащих user_id.
    """
    with get_db_session() as db:
        accounts = db.query(TelegramAccount).filter_by(user_id=user_id).all()
        result = []
        for account in accounts:
            result.append(
                {
                    "id": account.id,
                    "alias": account.alias,
                    "phone": account.phone,
                    "session_string": account.session_string,
                    "two_factor": account.two_factor,
                    "two_factor_pass": _decrypt_two_factor_pass(
                        account.two_factor_pass
                    ),
                    "is_monitoring": account.is_monitoring,
                    "is_taken": account.is_taken,
                    "created_at": account.created_at,
                    "updated_at": account.updated_at,
                }
            )
        return result


def update_telegram_account(acc: TelegramAccount, **kwargs):
    """
    Обновляет поля записи TelegramAccount (session_string, two_factor_pass, is_monitoring, ...).
    """
    with get_db_session() as db:
        db_acc = db.query(TelegramAccount).filter_by(id=acc.id).first()
        if not db_acc:
            return None

        try:
            for k, v in kwargs.items():
                setattr(db_acc, k, v)
            db_acc.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_acc)
            logger.info(f"Аккаунт id={acc.id} обновлён, поля={list(kwargs.keys())}")
            return db_acc
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при обновлении аккаунта: {e}")
            raise e


def delete_telegram_account(alias: str, phone: str) -> bool:
    """
    Удаляет аккаунт по alias и phone. Возвращает True, если удалён, иначе False.
    """
    with get_db_session() as db:
        account = db.query(TelegramAccount).filter_by(alias=alias, phone=phone).first()
        if not account:
            logger.warning(f"Аккаунт '{alias}' (phone={phone}) не найден для удаления.")
            return False

        try:
            db.delete(account)
            db.commit()
            logger.info(f"Аккаунт '{alias}' (phone={phone}) удалён.")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при удалении аккаунта: {e}")
            raise e
