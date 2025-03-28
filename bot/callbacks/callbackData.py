from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 5
ACCOUNT_PAGE_SIZE = 5


class UsersCallbackFactory(CallbackData, prefix="users"):
    action: str
    page: int = 1
    user_id: int = 0
    account_id: int = 0
    chat_id: int = 0


def get_accounts_keyboard(
    page: int, total_pages: int, user_id: int, accounts_on_page: list[dict]
) -> InlineKeyboardMarkup:
    """
    Создаём кнопки для аккаунтов + пагинацию.
    """
    kb = []
    # Кнопки "Подробнее"  или просто показываем alias
    for acc in accounts_on_page:
        btn = InlineKeyboardButton(
            text=f"{acc['alias']} ({acc['phone']})",
            callback_data=UsersCallbackFactory(
                action="account_chats",
                page=1,
                user_id=user_id,
                account_id=acc["id"],  # чтобы знать, какой аккаунт детально смотреть
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


def get_check_accounts(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Просмотреть аккаунты",
                    callback_data=UsersCallbackFactory(
                        action="user_accounts",
                        page=1,  # первая страница аккаунтов
                        user_id=user_id,
                    ).pack(),
                )
            ]
        ]
    )


def get_chats_keyboard(page, total_pages, account_id, chats_on_page):
    kb = [
        [
            InlineKeyboardButton(
                text=f"{chat['chat_name']} ({chat['msg_count']} сообщ.)",
                callback_data=UsersCallbackFactory(
                    action="chat_messages",
                    page=1,  # первая страница сообщений
                    account_id=account_id,
                    chat_id=chat["chat_id"],
                ).pack(),
            )
        ]
        for chat in chats_on_page
    ]

    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=UsersCallbackFactory(
                    action="account_chats",
                    page=page - 1,
                    account_id=account_id,
                ).pack(),
            )
        )
    if page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=UsersCallbackFactory(
                    action="account_chats",
                    page=page + 1,
                    account_id=account_id,
                ).pack(),
            )
        )

    if navigation_buttons:
        kb.append(navigation_buttons)

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_users_keyboard(
    page: int, total_pages: int, users_on_page: list[dict]
) -> InlineKeyboardMarkup:
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
