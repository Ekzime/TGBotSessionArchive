from aiogram.enums.chat_type import ChatType
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("admin_help"))
async def cmd_admin_help(messsage: types.Message):
    pass