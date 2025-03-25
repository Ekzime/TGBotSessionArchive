from aiogram import Router, types
from aiogram.filters import Command

router = Router()

help_text = """
Команды для работы с ботом.
<b>Команды:</b> 
    /start - начало работы.
    /register - регистрация профиля.
    /login - вход в аккаунт(Начать сеанс).
    /logout - закончить сеанс. 
    /give_tg - сдать тг в архив.
    /take_tg - взять тг с архива.
    /view_tg - просмотр сданных аккаунтов.

<b>Для начала работы, нужно сделать профиль и авторизоваться!</b>
"""


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(help_text)
