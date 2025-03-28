import logging
import math
from config import settings
from aiogram.filters import Command
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from bot import FSM
from bot.FSM.states import (
    LogGroupIdState,
    TimeoutStates,
    AdminNameStates,
    AdminIdsStates,
)
from bot.callbacks.callbackData import get_users_keyboard, PAGE_SIZE
from db.services.user_crud import delete_admin, set_new_admin, get_all_users
from db.services.telegram_crud import (
    get_telegram_account_by_alias,
    list_telegram_accounts,
)
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

help_text_for_admin = """<b>Каманды для админа:</b>\n\n 
/kill_session - удаление всех сессий на аккаунте за исключением бота. Полезно, если нужно выкинуть всех с аккаунта.\n
/get_info - выводит айди группы\n
/delete_admin - лешение прав по нику пользователя в боте, действует на всех\n
/set_admin - назначение прав администратора по нику пользователя в боте\n
/view_users - показывает всех пользователей бота\n
"""


@router.message(Command("help_admin"))
async def cmd_help_admin(message: types.Message):
    await message.answer(help_text_for_admin, parse_mode="HTML")


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
    acсount_dict = get_telegram_account_by_alias(alias=alias)
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
    await state.set_state(AdminIdsStates.wait_id)


@router.message(AdminIdsStates.wait_id)
async def get_id_for_new_admin(message: types.Message, state: FSMContext):
    msg_id = message.text.strip()
    try:
        set_new_admin(msg_id)
        await message.answer(
            f"Назначен новый администратор <b>username=</b> <code>{msg_id}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        # Ловим любые другие ошибки, которые могут возникнуть в CRUD-операциях
        logger.exception("Ошибка при назначении нового администратора")
        await message.answer(f"Ошибка при назначении нового администратора: {e}")
        await state.clear()
        return
    await state.clear()


@router.message(Command("delete_admin"))
async def cmd_delete_admin(message: types.Message, state: FSMContext):
    await message.answer(
        f"<b>Введите имя админа для снятия прав:</b>", parse_mode="HTML"
    )
    await state.set_state(AdminNameStates.wait_name)


@router.message(AdminNameStates.wait_name)
async def get_admin_name_for_delete(message: types.Message, state: FSMContext):
    name_msg = message.text.strip()
    result = delete_admin(username=name_msg)
    if result:
        logger.info(f"get_admin_name_for_delete: админ {name_msg} лишен прав!")
        await message.answer(
            f"Администратор <b>{name_msg}</b> лишен прав!", parse_mode="HTML"
        )
        state.clear()
        return
    else:
        await message.answer(f"{name_msg} не админ!")
        await state.clear()
        return


@router.message(Command("view_users"))
async def cmd_view_users(message: types.Message):
    all_users = get_all_users()
    if not all_users:
        await message.answer("Пользователи не найдены!")
        return

    page = 1
    total_pages = math.ceil(len(all_users) / PAGE_SIZE)

    # Берём срез пользователей на текущей странице
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    users_on_page = all_users[start_idx:end_idx]

    text = f"<b>Список пользователей (страница {page}/{total_pages}):</b>"
    keyboard = get_users_keyboard(page, total_pages, users_on_page)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
