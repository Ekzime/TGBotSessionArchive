from aiogram.enums.chat_type import ChatType
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("get_info"))
async def cmd_get_info_group(message: types.Message):
    # Проверяем, что команда вызвана в группе/супергруппе
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("Команду нужно вызывать в группе/супергруппе!")
        return

    group_id = message.chat.id
    await message.answer(f"Group ID: <code>{group_id}</code>", parse_mode="HTML")