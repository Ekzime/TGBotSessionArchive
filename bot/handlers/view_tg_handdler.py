from aiogram import Router, types
from aiogram.filters import Command
from db.models.model import User
from db.services.telegram_crud import list_telegram_accounts
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent
)
import uuid

router = Router()

# список аккаунтов в панеле, вызов через @botname view_tg
@router.inline_query()
async def inline_view_tg_handler(query: InlineQuery,current_user: User):
    if not query.query.lower().startswith("view_tg"):
        return  # не наша команда — игнор

    accounts = list_telegram_accounts(user_id=current_user.id)
    results = []

    for acc in accounts:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=acc["alias"],
                description=acc["phone"],
                input_message_content=InputTextMessageContent(
                    message_text=f"<b>2FA:</b> {'Включена' if acc.get('f2a') else 'Нет'}",
                    parse_mode="HTML"
                )
            )
        )

    await query.answer(results=results, cache_time=1, is_personal=True)

@router.message(Command('view_tg'))
async def cmd_view_tg(message: types.Message, current_user: User):
    accounts = list_telegram_accounts(user_id=current_user.id)
    if not accounts:
        await message.answer("Аккаунты не найдены!")
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