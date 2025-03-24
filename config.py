from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError
import logging

logger = logging.getLogger(__name__)

# централизированое управление переменными
class Settings(BaseSettings):
    TELEGRAM_BOT_API: str = Field(..., env="TELEGRAM_BOT_API")
    API_TELETHON_ID: int = Field(..., env="API_TELETHON_ID")
    API_TELETHON_HASH: str = Field(..., env="API_TELETHON_HASH")

    SQLALCHEMY_DATABASE_URL: str = Field(..., env="SQLALCHEMY_DATABASE_URL")
    FERNET_KEY: str = Field(..., env="FERNET_KEY")

    # временные типы
    LOGS_GROUP_ID: int = Field(..., env="LOGS_GROUP_ID")
    CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Configuration error: {e}")
    raise e
