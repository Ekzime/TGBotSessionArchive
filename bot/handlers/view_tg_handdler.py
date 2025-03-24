from aiogram import Router, types
from aiogram.filters import Command
from db.models.model import User
from db.services.telegram_crud import (
    list_telegram_accounts,
    get_telegram_account_by_telgram_id,
)
import logging
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
import uuid

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = Router()


@router.inline_query()
async def inline_view_tg_handler(query: InlineQuery) -> None:
    results = []

    if not query.query.lower().startswith("view_tg"):
        return  # игнорируем остальные inline-запросы

    user_dicr: dict = get_telegram_account_by_telgram_id(query.from_user.id)
    if not user_dicr:
        logger.error("inline_view_tg_handler: user_dict not found!")
        await query.answer(
            results=[],
            switch_pm_text="В базе данных ничего не найдено!",
            cache_time=1,
            is_personal=True,
        )
        return
    accounts = list_telegram_accounts(user_id=user_dicr["id"])

    if not accounts:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="Нет аккаунтов",
                input_message_content=InputTextMessageContent("У вас нет аккаунтов"),
            )
        )
    else:
        for acc in accounts:
            two_factor_enabled = acc.get("two_factor", False)
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=acc["alias"],
                    description=acc["phone"],
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"<b>Телеграм аккаунт:</b> {acc['alias']}\n"
                            f"<b>Номер:</b> {acc['phone']}\n"
                            f"<b>2FA:</b> {'Включена' if two_factor_enabled else 'Нет'}"
                        ),
                        parse_mode="HTML",
                    ),
                )
            )

    await query.answer(results=results, cache_time=1, is_personal=True)


@router.message(Command("view_tg"))
async def cmd_view_tg(message: types.Message, current_user: User) -> None:
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
