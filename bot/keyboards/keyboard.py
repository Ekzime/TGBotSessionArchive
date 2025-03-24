from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def default_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Взять ТГ", callback_data="take_tg"),
                InlineKeyboardButton(text="Сдать ТГ", callback_data="give_tg"),
            ],
            [
                InlineKeyboardButton(
                    text="Просмотреть ТГ", switch_inline_query_current_chat="view_tg"
                )
            ],
            [InlineKeyboardButton(text="Руководство", callback_data="management")],
        ]
    )
    return keyboard
