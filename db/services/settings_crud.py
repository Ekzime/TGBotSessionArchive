import logging
from db.models.model import BotSettings
from db.services.manager import get_db_session

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def set_logs_group_id(group_id: str):
    with get_db_session() as db:
        obj = db.query(BotSettings).filter_by(setting_key="LOGS_GROUP_ID").first()
        if obj:
            obj.setting_value = group_id
        else:
            # Создаём новую запись
            new_setting = BotSettings(
                setting_key="LOGS_GROUP_ID", setting_value=group_id
            )
            db.add(new_setting)

        db.commit()


def set_timeout_chek_chat(timeout: str):
    with get_db_session() as db:
        obj = db.query(BotSettings).filter_by(setting_key="CHECK_INTERVAL").first()
        if obj:
            obj.setting_value = timeout
        else:
            # Создаем новую запись
            new_setting = BotSettings(
                setting_key="CHECK_INTERVAL", setting_value=timeout
            )
            db.add(new_setting)

        db.commit()


def get_all_settings():
    with get_db_session() as db:
        rows = db.query(BotSettings).all()
        result = []
        for row in rows:
            result.append(
                {
                    "setting_key": row.setting_key,
                    "setting_value": row.setting_value,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
            )
        return result
