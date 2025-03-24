from aiogram import Router, types, F
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


@router.inline_query(F.query.lower().startswith("view_tg"))
async def inline_view_tg_handler(query: InlineQuery) -> None:
    """
    Показывает список Telegram-аккаунтов пользователя при вводе "view_tg".
    Если пользователь не авторизован или нет аккаунтов, возвращаем соответствующее сообщение.
    """
    # Проверяем, что пользователь ввёл "view_tg"
    if not query.query.lower().startswith("view_tg"):
        return  # пропускаем остальные inline-запросы

    # Пытаемся найти данные пользователя в БД
    user_data = get_telegram_account_by_telgram_id(query.from_user.id)
    if not user_data:
        # Если пользователь не найден (не авторизован и т.д.)
        logger.error("inline_view_tg_handler: user_data not found!")
        await query.answer(
            results=[],
            switch_pm_text=(
                "В базе данных ничего не найдено, либо вы не авторизованы.\n"
                "Для авторизации нажмите /login"
            ),
            # Если хотите кнопку "Перейти к боту", нужно указать непустой switch_pm_parameter
            # switch_pm_parameter="login",
            cache_time=1,
            is_personal=True,
        )
        return

    # Получаем список аккаунтов
    accounts = list_telegram_accounts(user_id=user_data["id"])

    # Формируем результаты для inline-запроса
    results = []
    if not accounts:
        # Если аккаунтов нет
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="Нет аккаунтов",
                input_message_content=InputTextMessageContent("У вас нет аккаунтов"),
            )
        )
    else:
        for acc in accounts:
            results.append(_build_inline_article(acc))

    # Отправляем результаты
    await query.answer(results=results, cache_time=1, is_personal=True)


def _build_inline_article(acc: dict) -> InlineQueryResultArticle:
    """
    Формирует InlineQueryResultArticle для одного аккаунта.
    """
    two_factor_enabled = acc.get("two_factor", False)
    text = (
        f"<b>Телеграм аккаунт:</b> <code>{acc['alias']}</code>\n"
        f"<b>Номер:</b> <code>{acc['phone']}</code>\n"
        f"<b>2FA:</b> {'Включена' if two_factor_enabled else 'Нет'}"
    )
    return InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title=acc["alias"],
        description=acc["phone"],
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
    )


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
