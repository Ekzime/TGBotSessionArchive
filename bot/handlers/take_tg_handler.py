import os
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from bot.FSM.states import TakeTgStates
from bot.handlers.give_tg_handler import router
from db.models.model import User
from db.services.telegram_crud import (
    get_telegram_account_by_phone,
    get_telegram_account_by_alias
)

router = Router()

@router.message(Command('take_tg'))
async def cmd_take_tg(message: types.Message, state: FSMContext):
    await message.answer("")
    await state.set_state()

@router.message(TakeTgStates.wait_alias)
async def take_tg_alias(message: types.Message, state: FSMContext,current_user: User):
    pass