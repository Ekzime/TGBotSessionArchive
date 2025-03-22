from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime,
    ForeignKey, Integer, String,
    BigInteger, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship(
        "UserSession",
        back_populates='user',
        cascade='all,delete'
    )

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    telegram_user_id = Column(String(50), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")

class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    alias = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    session_string = Column(String(2048), nullable=False)

    two_factor = Column(Boolean, default=False)
    two_factor_pass = Column(String(255), nullable=True)

    is_monitoring = Column(Boolean, default=False)  # включена ли прослушка
    is_taken = Column(Boolean, default=False)       # "в руках" у менеджера или нет

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship(
        "TelegramMessage",
        back_populates="account",
        cascade="all, delete"
    )

class TelegramMessage(Base):
    """
    Таблица для хранения переписки, которую бот сохраняет при прослушке.
    """
    __tablename__ = "telegram_messages"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"))

    chat_id = Column(BigInteger, nullable=False)     # ID чата в Telegram
    message_id = Column(BigInteger, nullable=False)  # ID сообщения в чате
    sender_id = Column(BigInteger, nullable=True)    # ID отправителя (может быть менеджер или лидер)
    text = Column(Text, nullable=True)               # текст сообщения (если есть)
    date = Column(DateTime, nullable=True)           # дата/время отправки
    deleted_at = Column(DateTime, nullable=True)     # когда сообщение было удалено (NULL, если не удалено)

    # Новые поля:
    logs_msg_id = Column(BigInteger, nullable=True)  # ID пересланного сообщения в логовой группе
    media_type = Column(String(50), nullable=True)   # "voice", "document", "photo", etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("TelegramAccount", back_populates="messages")
