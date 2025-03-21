from aiogram import Router, types
from aiogram.filters import Command
from pyexpat.errors import messages

router = Router()

wellcom_text = """
Добро пожаловать в архив аккаунтов!
<b>Команды:</b> 
    /start - начало работы.
    /register - регистрация профиля.
    /login - вход в аккаунт.
    /logout - закончить сеанс. 
    /give_tg - сдать тг в архив.
    /take_tg - взять тг с архива.
    /view_tg - просмотр сданных аккаунтов.
    
<b>Для начала работы, нужно сделать профиль и авторизоваться!</b>
"""

@router.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(wellcom_text,parse_mode="HTML")