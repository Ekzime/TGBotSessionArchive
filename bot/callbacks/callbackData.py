from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 5
ACCOUNT_PAGE_SIZE = 5


class UsersCallbackFactory(CallbackData, prefix="users"):
    action: str  # "page", "details", "user_accounts", "account_details", ...
    page: int
    user_id: int = 0
    account_id: int = 0


def get_users_keyboard(
    page: int, total_pages: int, users_on_page: list[dict]
) -> InlineKeyboardMarkup:
    """
    Пагинация для списка пользователей (у вас это уже есть).
    """
    kb = []
    for user in users_on_page:
        btn = InlineKeyboardButton(
            text=f"{user['username']} (Подробнее)",
            callback_data=UsersCallbackFactory(
                action="details", page=page, user_id=user["id"]
            ).pack(),
        )
        kb.append([btn])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=UsersCallbackFactory(action="page", page=page - 1).pack(),
            )
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=UsersCallbackFactory(action="page", page=page + 1).pack(),
            )
        )
    if nav_buttons:
        kb.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_accounts_keyboard(
    page: int, total_pages: int, user_id: int, accounts_on_page: list[dict]
) -> InlineKeyboardMarkup:
    """
    Пагинация для аккаунтов конкретного пользователя.
    """
    kb = []
    for acc in accounts_on_page:
        btn = InlineKeyboardButton(
            text=f"{acc['alias']} ({acc['phone']})",
            callback_data=UsersCallbackFactory(
                action="account_details",
                page=page,
                user_id=user_id,
                account_id=acc["id"],
            ).pack(),
        )
        kb.append([btn])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=UsersCallbackFactory(
                    action="user_accounts", page=page - 1, user_id=user_id
                ).pack(),
            )
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=UsersCallbackFactory(
                    action="user_accounts", page=page + 1, user_id=user_id
                ).pack(),
            )
        )
    if nav_buttons:
        kb.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=kb)
