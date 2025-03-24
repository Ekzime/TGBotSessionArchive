from pydantic import BaseSettings, Field, ValidationError
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    TELEGRAM_BOT_API = Field(...,env="TELEGRAM_BOT_API")
    API_TELETHON_ID: int = Field(..., env="API_TELETHON_ID")
    API_TELETHON_HASH: str = Field(..., env="API_TELETHON_HASH")

    SQLALCHEMY_DATABASE_URL = Field(...,env="SQLALCHEMY_DATABASE_URL")
    FERNET_KEY = Field(...,env="FERNET_KEY")
    
    LOGS_GROUP_ID: int = Field(..., env="LOGS_GROUP_ID")
    CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Configuration error: {e}")
    raise e