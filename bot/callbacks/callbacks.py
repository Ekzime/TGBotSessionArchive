from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.handlers.give_tg_handler import cmd_give_tg
from bot.handlers.take_tg_handler import cmd_take_tg
from bot.handlers.view_tg_handdler import cmd_view_tg

router = Router()

@router.callback_query(F.data == "give_tg")
async def callback_give_tg(callback: types.CallbackQuery, state: FSMContext) -> None:
    await cmd_give_tg(callback.message,state)
    await callback.answer()

@router.callback_query(F.data== "take_tg")
async def callback_take_tg(callback: types.Message, state: FSMContext) -> None:
    await cmd_take_tg(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "view_tg")
async def callback_view_tg(callback: types.Message) -> None:
    await cmd_view_tg(callback.message)
    await callback.answer()

@router.callback_query(F.data == "management")
async def callback_management(callback: types.CallbackQuery):
    await callback.answer("Link to managemet!") # TODO: доделать ссылку на руководство!