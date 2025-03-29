import stat
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from bot.handlers.give_tg_handler import cmd_give_tg
from bot.handlers.take_tg_handler import cmd_take_tg
from db.services.telegram_crud import (
    get_telegram_account_by_id,
    get_telegram_account_by_alias,
)
from bot.FSM.states import TakeTgStates


router = Router()


@router.callback_query(F.data == "give_tg")
async def callback_give_tg(callback: types.CallbackQuery, state: FSMContext) -> None:
    await cmd_give_tg(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "take_tg")
async def callback_take_tg(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "<b>Введите имя аккаунта для выдачи:</b>", parse_mode="HTML"
    )
    await callback.answer("Выдача телеграмма")
    await state.set_state(TakeTgStates.wait_alias)
    await callback.answer()


@router.message(TakeTgStates.wait_alias)
async def callback_get_alias_tg(message: types.Message, state: FSMContext):
    user_data = get_telegram_account_by_alias(message.text.strip())
    if not user_data:
        await message.answer("Не найдено пользователя!")
        return
    alias = message.text.strip()
    await cmd_take_tg(message=message, current_user=user_data["id"], alias=alias)
    await state.clear()


# TODO: доделать ссылку на руководство!
@router.callback_query(F.data == "management")
async def callback_management(callback: types.CallbackQuery):
    await callback.message.answer("https://telegra.ph/Kak-rabotaet-03-24")
    await callback.answer()
