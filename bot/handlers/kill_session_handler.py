from aiogram import Router, types
from aiogram.filters import Command
from telethon import TelegramClient
from telethon.sessions import StringSession
from db.models.model import User
from db.services.telegram_crud import get_telegram_account_by_alias
import os
from config import settings
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest

API_TELETHON_ID = settings.API_TELETHON_ID
API_TELETHON_HASH = settings.API_TELETHON_HASH

router = Router()

@router.message(Command('kill_session'))
async def cmd_kill_session(message: types.Message, current_user: User):
    '''
        Убивает все сессии активные на аккаунте, кроме сессии бота.
        prim: /kill_session <alias>
    '''
    # проверка на корректность ожидаемого ввода
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /cleanup_sessions <alias>")
        return

    # берем alias + user_id и ищем его в БД
    alias = parts[1].strip()
    acсount_dict = get_telegram_account_by_alias(current_user.id,alias)
    if not acсount_dict:
        await message.answer("Аккаунт для убийства сессий не найден.")
        return

    # если аккаунт есть в БД, подключение к сессии аккаунта.
    session_str = acсount_dict['session_string']
    client = TelegramClient(StringSession(session_str), API_TELETHON_ID,API_TELETHON_HASH)
    await client.connect()
    try:
        auths = await client(GetAuthorizationsRequest())
        # kill session
        for a in auths.authorizations:
            if not a.current:
                await client(ResetAuthorizationRequest(a.hash))

        await message.answer(f"Все сессии (кроме текущей) для аккаунта <b>{alias}</b> убиты.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка очистки: {e}")
    finally:
        await client.disconnect()

