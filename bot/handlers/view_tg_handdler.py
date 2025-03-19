from aiogram import Router, types
from aiogram.filters import Command
from db.models.model import User
from db.services.telegram_crud import list_telegram_accounts

router = Router()

@router.message(Command('view_tg'))
async def cmd_view_tg(message: types.Message, current_user: User):
    accounts = list_telegram_accounts(user_id=current_user.id)
    if not accounts:
        await message.answer("Аккаунты не найдены! Проверьте подключение к БД!")
    else:
        msg_text = "<b>Список ваших аккаунтов:</b>\n\n"
        for acc in accounts:
            msg_text += (
                f"name: <code>{acc['alias']}</code>\n"
                f"phone: <code>{acc['phone']}</code>\n"
                f"f2a_pass: <code>{acc['two_factor_pass']}</code>\n"
                "------------\n"
            )
        await message.answer(msg_text, parse_mode="HTML")