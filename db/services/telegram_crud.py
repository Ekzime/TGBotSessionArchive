import logging
from datetime import datetime

from db.models.model import TelegramAccount
from db.services.manager import get_db_session
from bot.utils.crypto import encrypt_text, decrypt_text

logger = logging.getLogger(__name__)

def _decrypt_two_factor_pass(two_factor_pass: str):
    return decrypt_text(two_factor_pass) if two_factor_pass else None

def _encrypt_two_factor_pass(two_factor_pass: str):
    return encrypt_text(two_factor_pass) if two_factor_pass else None

def create_telegram_account(user_id: int,
                            alias: str,
                            phone: str,
                            session_string: str = None,
                            two_factor: bool = False,
                            two_factor_pass: str = None):
    """
    Создаёт запись в telegram_accounts с проверками и обработкой ошибок.
    """
    with get_db_session() as db:
        # проверка на наличие данных в переменных
        if not user_id or not alias or not phone:
            raise ValueError("user_id, alias, and phone are required fields")

        # Проверка, что аккаунта с таким телефоном или alias еще нет
        existing_account = db.query(TelegramAccount).filter(
            (TelegramAccount.phone == phone) | (TelegramAccount.alias == alias)  # type: ignore
        ).first()
        if existing_account:
            raise ValueError(f"Телеграм аккаунт: '{phone}' либо элиас '{alias}' уже есть!")

        account = TelegramAccount(
            user_id=user_id,
            alias=alias,
            phone=phone,
            session_string=session_string,
            two_factor=two_factor,
            two_factor_pass=_encrypt_two_factor_pass(two_factor_pass),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()  # Можно сделать через модель: onupdate=datetime.utcnow
        )

        try:
            db.add(account)
            db.commit()
            db.refresh(account)
            logger.info(f"Телеграм аккаунт успешно сохранен в базе данных: {account.id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка сохранения аккаунта в базе данных: {e}")
            raise e

        return account

def get_telegram_account_by_alias(user_id: int, alias: str):
    """
       Возвращает одну запись TelegramAccount (или None) по alias и user_id.
    """
    with get_db_session() as db:
        account = db.query(TelegramAccount).filter_by(user_id=user_id, alias=alias).first()
        if account:
            return {
                "id": account.id,
                "alias": account.alias,
                "phone": account.phone,
                "session_string": account.session_string,
                "two_factor":account.two_factor,
                "two_factor_pass":_decrypt_two_factor_pass(account.two_factor_pass)
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
            result.append({
                "id": account.id,
                "alias": account.alias,
                "phone": account.phone,
                "session_string": account.session_string,
                "two_factor": account.two_factor,
                "two_factor_pass": _decrypt_two_factor_pass(account.two_factor_pass)
            })
        return result


def update_telegram_account(acc: TelegramAccount, **kwargs):
    """
    Обновляет поля записи TelegramAccount.
    Например: session_string, two_factor_pass, ...
    """
    with get_db_session() as db:
        for k, v in kwargs.items():
            setattr(acc, k, v)
        acc.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(acc)
        return acc

def decrypt_two_factor_pass(acc: TelegramAccount):
    """
    Расшифровывает two_factor_pass (если есть).
    """
    if not acc.two_factor_pass:
        return None
    return decrypt_text(acc.two_factor_pass)

def get_telegram_account_by_phone(user_id: int, phone: str):
    with get_db_session() as db:
        account = db.query(TelegramAccount).filter_by(user_id=user_id, phone=phone).first()
        if account:
            # Возвращаем только нужные данные простых типов, не объект модели целиком
            return {
                "id": account.id,
                "alias": account.alias,
                "phone": account.phone,
                "session_string": account.session_string,
                "two_factor": account.two_factor,
                "two_factor_pass": _decrypt_two_factor_pass(account.two_factor_pass)
            }
        return None