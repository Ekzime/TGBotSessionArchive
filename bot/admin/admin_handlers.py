import logging
from config import settings
from aiogram.filters import Command
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from bot import FSM
from bot.FSM.states import LogGroupIdState, TimeoutStates, AdminStates
from db.services.settings_crud import (
    set_logs_group_id,
    get_all_settings,
    set_timeout_chek_chat,
)
from db.services.user_crud import set_new_admin
from db.services.telegram_crud import get_telegram_account_by_alias
from telethon.tl.functions.account import (
    GetAuthorizationsRequest,
    ResetAuthorizationRequest,
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from db.models.model import User
from aiogram.enums.chat_type import ChatType


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


API_TELETHON_ID = settings.API_TELETHON_ID
API_TELETHON_HASH = settings.API_TELETHON_HASH

router = Router()

help_text_for_admin = """<b>Каманды для админа:</b>\n\n /bind - привязка бота к группе, в которой он будет хранить файлы. В БД файлы хранить нельзя. Группа для логов может быть только одна, и бот должен быть админом!\n
/setting - настройки бота, показывает айди группы к которой привязан, также таймаут для чекера чатов.\n
/timeout - установить таймаут для чекера чтение/запись чатов\n
/kill_session - удаление всех сессий на аккаунте за исключением бота. Полезно, если нужно выкинуть всех с аккаунта.\n
/get_info - выводит айди группы
"""


@router.message(Command("help_admin"))
async def cmd_help_admin(message: types.Message):
    await message.answer(help_text_for_admin, parse_mode="HTML")


@router.message(Command("bind"))
async def cmd_bind_admin(message: types.Message, state: FSMContext):
    """Записывает айди чата, в который нужно переслать файлы"""
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("Команду нужно вызывать в группе/супергруппе!")
        return
    await message.answer("<b>Введите айди чата для привязки:</b>", parse_mode="HTML")
    await state.set_state(LogGroupIdState.wait_group_id)


@router.message(LogGroupIdState.wait_group_id)
async def get_chat_id_for_log_group(message: types.Message, state: FSMContext):
    """Ожидаем сообщение от админа с новым значеним для LOG_GROUP_ID"""
    group_id = message.text.strip()
    if len(group_id) <= 5:
        await message.answer("Введите корректное айди группы для команды /bind!")
        await state.clear()
        return
    if group_id:
        try:
            set_logs_group_id(group_id=group_id)
            logger.info(f"Get_chat_id_for_log_group: Bind bot to group={group_id}")
            await message.answer(
                f"Установлена логовая группа: <code>{group_id}</code>",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(
                "Get_chat_id_for_log_group: Ошибка привязки бота к логовой группе!"
            )
            await message.answer(
                f"<b>Произошла ошибка привязки:</b> {e}", parse_mode="HTML"
            )

    await state.clear()


@router.message(Command("settings"))
async def cmd_get_settings(message: types.Message):
    """Выводит текущие настройки указаные в БД"""
    bot_settings = get_all_settings()
    if not bot_settings:
        await message.answer("Настройки не найдены!")
        return

    msg_text = "<b>Список настроек:</b>\n\n"
    for setting in bot_settings:
        msg_text += (
            f"KEY: <code>{setting['setting_key']}</code>\n"
            f"VALUE: <code>{setting['setting_value']}</code>\n"
            "----------\n"
        )

    await message.answer(msg_text, parse_mode="HTML")


@router.message(Command("timeout"))
async def cmd_set_timeout(message: types.Message, state: FSMContext):
    """Установка тайм аута для чекера"""
    await message.answer(
        "<b>Крайне не рекомендуется устанавливать низкий интервал для чекера чатов!\n Оптимальный вариант от 10-15.</b>",
        parse_mode="HTML",
    )
    await message.answer("<b>Введите таймаут для черека:</b>", parse_mode="HTML")
    await state.set_state(TimeoutStates.wait_timeout)


@router.message(TimeoutStates.wait_timeout)
async def get_timeout(message: types.Message, state: FSMContext):
    """Ожидаем новое значение, записываем в БД"""
    timeout_msg = message.text.strip()
    if timeout_msg:
        if not len(timeout_msg) > 1:
            await message.answer(
                "Недопустимое значение, меньше 10 быть не может! Введите заново /timeout"
            )
            state.clear()
            return
        try:
            set_timeout_chek_chat(timeout_msg)
            logger.info(f"Get_timeout: set timeout={timeout_msg}")
            await message.answer(
                f"Установлен новый таймаут для чекера: timeout={timeout_msg}"
            )
        except Exception as e:
            logger.error(f"Get_timeout: Ошибка в назначении нового таймаута: {e}")
            await message.answer(
                f"<b>Ошибка в записи нового таймаута:</b> {e}", parse_mode="HTML"
            )
    await state.clear()


@router.message(Command("kill_session"))
async def cmd_kill_session(message: types.Message, current_user: User):
    """
    Убивает все сессии активные на аккаунте, кроме сессии бота.
    prim: /kill_session <alias>
    """
    # проверка на корректность ожидаемого ввода
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /cleanup_sessions <alias>")
        return

    # берем alias + user_id и ищем его в БД
    alias = parts[1].strip()
    acсount_dict = get_telegram_account_by_alias(current_user.id, alias)
    if not acсount_dict:
        await message.answer("Аккаунт для убийства сессий не найден.")
        return

    # если аккаунт есть в БД, подключение к сессии аккаунта.
    session_str = acсount_dict["session_string"]
    client = TelegramClient(
        StringSession(session_str), API_TELETHON_ID, API_TELETHON_HASH
    )
    await client.connect()
    try:
        auths = await client(GetAuthorizationsRequest())
        # kill session
        for a in auths.authorizations:
            if not a.current:
                await client(ResetAuthorizationRequest(a.hash))

        await message.answer(
            f"Все сессии (кроме текущей) для аккаунта <b>{alias}</b> убиты.",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Ошибка очистки: {e}")
    finally:
        await client.disconnect()


@router.message(Command("get_info"))
async def cmd_get_info_group(message: types.Message):
    # Проверяем, что команда вызвана в группе/супергруппе
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("Команду нужно вызывать в группе/супергруппе!")
        return

    group_id = message.chat.id
    await message.answer(f"Group ID: <code>{group_id}</code>", parse_mode="HTML")


@router.message(Command("set_admin"))
async def cmd_set_new_admin(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите <b>username</b> что бы назначить нового админа:", parse_mode="HTML"
    )
    await state.set_state(AdminStates.wait_ids)


@router.message(AdminStates.wait_ids)
async def get_id_for_new_admin(message: types.Message, state: FSMContext):
    msg_id = message.text.strip()
    try:
        set_new_admin(msg_id)
        await message.answer(
            f"Назначен новый администратор <b>username=</b> <code>{msg_id}</code>"
        )
    except Exception as e:
        # Ловим любые другие ошибки, которые могут возникнуть в CRUD-операциях
        logger.exception("Ошибка при назначении нового администратора")
        await message.answer(f"Ошибка при назначении нового администратора: {e}")
        await state.clear()
        return
    await state.clear()

@router.message(Command('delete_admin'))
async def cmd_delete_admin(message: types.Message, state: FSMContext):
    await message.answer(f"<b>Введите имя админа для снятия прав:</b>")
    await state.set_state(AdminStates.wait_ids)

@router.message(AdminStates.wait_ids)
async def get_admin_name_for_delete(message: types.Message, state: FSMContext):
    await 