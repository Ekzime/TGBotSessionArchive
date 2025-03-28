from aiogram import types, Router
from bot.callbacks.callbackData import (
    UsersCallbackFactory,
    PAGE_SIZE,
    get_users_keyboard,
    ACCOUNT_PAGE_SIZE,
)
from db.services.user_crud import get_all_users
from db.services.telegram_crud import list_telegram_accounts
from bot.callbacks.callbackData import get_users_keyboard, get_accounts_keyboard
import math


router = Router()


@router.callback_query(UsersCallbackFactory.filter())
async def process_users_callback(
    query: types.CallbackQuery, callback_data: UsersCallbackFactory
):
    all_users: None | list = get_all_users()
    if not all_users:
        await query.message.edit_text("Пользователи не найдены!")
        await query.answer()
        return

    total_pages = math.ceil(len(all_users) / PAGE_SIZE)

    # 1) ПАГИНАЦИЯ ПОЛЬЗОВАТЕЛЕЙ
    if callback_data.action == "page":
        page = callback_data.page
        if page < 1 or page > total_pages:
            await query.answer("Некорректная страница!", show_alert=True)
            return

        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        users_on_page = all_users[start_idx:end_idx]

        text = f"<b>Список пользователей (страница {page}/{total_pages}):</b>"
        keyboard = get_users_keyboard(page, total_pages, users_on_page)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await query.answer()

    # 2) ДЕТАЛИ ПОЛЬЗОВАТЕЛЯ + кнопка "Просмотреть аккаунты"
    elif callback_data.action == "details":
        user_id = callback_data.user_id
        user_obj = next((u for u in all_users if u["id"] == user_id), None)
        if not user_obj:
            await query.answer("Пользователь не найден!", show_alert=True)
            return

        accounts = list_telegram_accounts(user_id)
        total_accounts = len(accounts)
        monitored_count = sum(1 for acc in accounts if acc.get("is_monitoring"))

        details_text = (
            f"<b>Профиль пользователя:</b>\n\n"
            f"Username: <code>{user_obj['username']}</code>\n"
            f"Admin: <code>{user_obj['is_admin']}</code>\n\n"
            f"Всего аккаунтов: <code>{total_accounts}</code>\n"
            f"Мониторятся: <code>{monitored_count}</code>"
        )

        # Кнопка "Просмотреть аккаунты" (ведёт к action="user_accounts")
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Просмотреть аккаунты",
                        callback_data=UsersCallbackFactory(
                            action="user_accounts",
                            page=1,  # Первая страница аккаунтов
                            user_id=user_id,
                        ).pack(),
                    )
                ]
            ]
        )

        # Скрываем клавиатуру списка пользователей
        await query.message.edit_reply_markup(None)
        # Отправляем новое сообщение с кнопкой
        await query.message.answer(details_text, reply_markup=kb, parse_mode="HTML")
        await query.answer()

    # 3) ПАГИНАЦИЯ АККАУНТОВ ПОЛЬЗОВАТЕЛЯ
    elif callback_data.action == "user_accounts":
        user_id = callback_data.user_id
        user_obj = next((u for u in all_users if u["id"] == user_id), None)
        if not user_obj:
            await query.answer("Пользователь не найден!", show_alert=True)
            return

        accounts = list_telegram_accounts(
            user_id
        )  # -> список словарей [{"id":..., "alias":..., "phone":..., ...}, ...]
        if not accounts:
            await query.message.edit_text("У пользователя нет аккаунтов!")
            await query.answer()
            return

        total_acc_pages = math.ceil(len(accounts) / ACCOUNT_PAGE_SIZE)
        page = callback_data.page
        if page < 1 or page > total_acc_pages:
            await query.answer("Некорректная страница аккаунтов!", show_alert=True)
            return

        start_idx = (page - 1) * ACCOUNT_PAGE_SIZE
        end_idx = start_idx + ACCOUNT_PAGE_SIZE
        accounts_on_page = accounts[start_idx:end_idx]

        text = f"<b>Аккаунты пользователя:</b>\n\n" f"Страница {page}/{total_acc_pages}"

        keyboard = get_accounts_keyboard(
            page, total_acc_pages, user_id, accounts_on_page
        )
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await query.answer()

    # 4) Детальный просмотр конкретного аккаунта (если хотите)
    elif callback_data.action == "account_details":
        # Если нужно детально смотреть 1 аккаунт
        user_id = callback_data.user_id
        account_id = callback_data.account_id

        # Загружаем аккаунты, ищем нужный
        accounts = list_telegram_accounts(user_id)
        account_obj = next((a for a in accounts if a["id"] == account_id), None)
        if not account_obj:
            await query.answer("Аккаунт не найден!", show_alert=True)
            return

        details_text = (
            f"<b>Аккаунт:</b>\n"
            f"Alias: <code>{account_obj['alias']}</code>\n"
            f"Phone: <code>{account_obj['phone']}</code>\n"
            f"Мониторинг: <b>{account_obj['is_monitoring']}</b>\n"
        )
        # Просто редактируем сообщение или отправляем новое
        await query.message.edit_text(details_text, parse_mode="HTML")
        await query.answer()
