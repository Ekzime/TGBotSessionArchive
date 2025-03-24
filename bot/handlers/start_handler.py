from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards.keyboard import default_menu

router = Router()

text = "<b>Выберите действие:</b>"

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(text,parse_mode="HTML",reply_markup=default_menu())