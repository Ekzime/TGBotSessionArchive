from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    BigInteger,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TimestampMixin:
    """Миксин для автоматического управления датами создания и обновления."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    telegram_user_id = Column(String(50), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class TelegramAccount(Base, TimestampMixin):
    __tablename__ = "telegram_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    alias = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    session_string = Column(String(2048), nullable=False)

    two_factor = Column(Boolean, default=False, nullable=False)
    two_factor_pass = Column(String(255), nullable=True)

    is_monitoring = Column(
        Boolean, default=False, nullable=False
    )  # включена ли прослушка
    is_taken = Column(
        Boolean, default=False, nullable=False
    )  # "в руках" у менеджера или нет

    messages = relationship(
        "TelegramMessage", back_populates="account", cascade="all, delete-orphan"
    )

    # Связь с пользователем для удобного доступа
    user = relationship("User", backref="telegram_accounts")

    def __repr__(self):
        return f"<TelegramAccount(id={self.id}, alias='{self.alias}', phone='{self.phone}')>"


class TelegramMessage(Base, TimestampMixin):
    """
    Таблица для хранения переписки, которую бот сохраняет при прослушке.
    """

    __tablename__ = "telegram_messages"

    id = Column(Integer, primary_key=True)
    account_id = Column(
        Integer, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False
    )

    chat_id = Column(BigInteger, nullable=False)  # ID чата в Telegram
    message_id = Column(BigInteger, nullable=False)  # ID сообщения в чате
    sender_id = Column(
        BigInteger, nullable=True
    )  # ID отправителя (может быть менеджер или лидер)
    text = Column(Text, nullable=True)  # текст сообщения (если есть)
    date = Column(DateTime, nullable=True)  # дата/время отправки
    deleted_at = Column(
        DateTime, nullable=True
    )  # когда сообщение было удалено (NULL, если не удалено)

    # Новые поля:
    logs_msg_id = Column(
        BigInteger, nullable=True
    )  # ID пересланного сообщения в логовой группе
    media_type = Column(String(50), nullable=True)  # "voice", "document", "photo", etc.

    account = relationship("TelegramAccount", back_populates="messages")

    def __repr__(self):
        return f"<TelegramMessage(id={self.id}, chat_id={self.chat_id}, message_id={self.message_id})>"


class BotSettings(Base):
    """Таблица для хранения ключ-значение настроек бота."""

    __tablename__ = "bot_settings"

    setting_key = Column(String(100), primary_key=True)
    setting_value = Column(
        String(255), nullable=False
    )  # исправлено: добавлена длина для MySQL
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<BotSettings(key='{self.setting_key}', value='{self.setting_value}')>"
