from pathlib import Path
from aiogram.types import FSInputFile
import math
import logging
from aiogram import Router, types
from bot.callbacks.callbackData import (
    UsersCallbackFactory,
    PAGE_SIZE,
    get_users_keyboard,
    ACCOUNT_PAGE_SIZE,
    get_check_accounts,
    get_accounts_keyboard,
    get_chats_keyboard,
)
from db.services.user_crud import get_all_users
from db.services.telegram_crud import (
    list_telegram_accounts,
    list_chats_for_account,
    get_chat_messages,
    get_telegram_account_by_id,
    get_sender_display_name,
)
from jinja2 import Environment, FileSystemLoader
import base64
import tempfile
import os
import os.path

logger = logging.getLogger(__name__)

router = Router()

env = Environment(
    loader=FileSystemLoader("bot/templates")
)  # Папка, где хранится chat.html
template = env.get_template("chat.html")


def generate_chat_html(chat_id: int, messages: list[dict]) -> str:
    """
    Генерирует HTML, встраивая картинки/медиа (фото, видео, голосовые, etc.) в Base64.
    Возвращает строку HTML (Unicode).
    """
    for m in messages:
        media_path = m.get("media_path")
        if media_path and os.path.exists(media_path):
            with open(media_path, "rb") as f:
                data = f.read()
            # base64
            m["embed_b64"] = base64.b64encode(data).decode("utf-8")
        else:
            m["embed_b64"] = None

        # "голоса" (ogg/opus) => voice, mp4 => video, jpg/png => photo, иначе document
        if not m.get("media_type"):
            ext = os.path.splitext(media_path or "")[1].lower()
            if ext in (".jpg", ".jpeg", ".png"):
                m["media_type"] = "photo"
            elif ext in (".ogg", ".opus"):
                m["media_type"] = "voice"
            elif ext in (".mp4", ".mov"):
                m["media_type"] = "video"
            else:
                m["media_type"] = "document"

    html_out = template.render(chat_id=chat_id, messages=messages)
    return html_out


@router.callback_query(UsersCallbackFactory.filter())
async def process_users_callback(
    query: types.CallbackQuery, callback_data: UsersCallbackFactory
):
    all_users = get_all_users()
    if not all_users:
        await query.message.edit_text("Пользователи не найдены!")
        await query.answer()
        return

    total_pages = math.ceil(len(all_users) / PAGE_SIZE)

    # Переключение страниц (список пользователей)
    if callback_data.action == "page":
        page = callback_data.page
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        users_on_page = all_users[start_idx:end_idx]

        text = f"<b>Список пользователей (страница {page}/{total_pages}):</b>"
        keyboard = get_users_keyboard(page, total_pages, users_on_page)

        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await query.answer()

    # Подробнее о пользователе
    elif callback_data.action == "details":
        user_id = callback_data.user_id
        user_obj = next((u for u in all_users if u["id"] == user_id), None)
        if not user_obj:
            await query.answer("Пользователь не найден!", show_alert=True)
            return

        # Получаем общее количество аккаунтов, если надо сразу показать
        accounts = list_telegram_accounts(user_id)
        total_accounts = len(accounts)
        monitored_count = sum(1 for acc in accounts if acc.get("is_monitoring"))

        details_text = (
            f"<b>Профиль пользователя:</b>\n\n"
            f"ID: <code>{user_obj['id']}</code>\n"
            f"Username: <code>{user_obj['username']}</code>\n"
            f"Admin: <code>{user_obj['is_admin']}</code>\n\n"
            f"Всего аккаунтов: <code>{total_accounts}</code>\n"
            f"Мониторятся: <code>{monitored_count}</code>"
        )

        # Кнопка "Просмотреть аккаунты"
        kb = get_check_accounts(user_id)

        # Скрываем клавиатуру списка пользователей (чтобы не нажимали снова)
        await query.message.edit_reply_markup(None)
        # Отправляем новое сообщение с кнопкой
        await query.message.answer(details_text, reply_markup=kb, parse_mode="HTML")
        await query.answer()

    # Просмотр аккаунтов пользователя с пагинацией
    elif callback_data.action == "user_accounts":
        user_id = callback_data.user_id
        # Снова найдём пользователя, если нужно (или пропустим, если не надо)
        user_obj = next((u for u in all_users if u["id"] == user_id), None)
        if not user_obj:
            await query.answer("Пользователь не найден!", show_alert=True)
            return

        # Загружаем аккаунты
        accounts = list_telegram_accounts(user_id)
        if not accounts:
            await query.message.edit_text("У пользователя нет аккаунтов!")
            await query.answer()
            return

        # Пагинация аккаунтов
        page = callback_data.page
        total_acc_pages = math.ceil(len(accounts) / ACCOUNT_PAGE_SIZE)

        # Проверяем границы
        if page < 1 or page > total_acc_pages:
            await query.answer("Некорректная страница!", show_alert=True)
            return

        start_idx = (page - 1) * ACCOUNT_PAGE_SIZE
        end_idx = start_idx + ACCOUNT_PAGE_SIZE
        accounts_on_page = accounts[start_idx:end_idx]

        # Формируем текст + клавиатуру аккаунтов
        text = (
            f"<b>Аккаунты пользователя:</b>\n\n" f"Страница {page}/{total_acc_pages}\n"
        )

        keyboard = get_accounts_keyboard(
            page, total_acc_pages, user_id, accounts_on_page
        )

        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await query.answer()

    # Пагинация списка чатов аккаунта
    elif callback_data.action == "account_chats":
        account_id = callback_data.account_id
        chats = list_chats_for_account(account_id)
        if not chats:
            await query.message.edit_text("📭 У этого аккаунта нет сохранённых чатов!")
            await query.answer()
            return

        total_pages = math.ceil(len(chats) / PAGE_SIZE)
        page = callback_data.page
        if page < 1 or page > total_pages:
            await query.answer("Некорректная страница чатов!", show_alert=True)
            return

        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        chats_on_page = chats[start_idx:end_idx]

        keyboard = get_chats_keyboard(page, total_pages, account_id, chats_on_page)
        await query.message.edit_text(
            f"<b>📁 Список чатов аккаунта (стр. {page}/{total_pages}):</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await query.answer()
    elif callback_data.action == "chat_messages":
        account_id = callback_data.account_id
        chat_id = callback_data.chat_id

        messages = get_chat_messages(account_id, chat_id)
        if not messages:
            await query.message.edit_text("В этом чате нет сообщений!")
            await query.answer()
            return

        # 1) Определяем local_id (кто "мы")
        acc_dict = get_telegram_account_by_id(account_id)
        alias = acc_dict["alias"]
        user_id = acc_dict["user_id"]

        # 2) Дополним поля в messages
        for m in messages:
            m["sender_str"] = m.get("sender_name") or m.get("chat_name", "Собеседник")

            # filename для скачивания
            if m.get("media_path"):
                m["filename"] = os.path.basename(m["media_path"])
            else:
                m["filename"] = "file.bin"
        # 3) Формируем HTML
        html_content = generate_chat_html(chat_id, messages)

        # 5) Записываем во временный файл (UTF-8!)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, suffix=".html"
        ) as tmp:
            tmp.write(html_content)
            tmp_path = tmp.name

        await query.message.edit_text("Формируем общий HTML-файл...")
        await query.answer()

        # 6) Отправляем файл
        await query.message.answer_document(
            FSInputFile(tmp_path), caption=f"История чата {chat_id}"
        )
        os.remove(tmp_path)
