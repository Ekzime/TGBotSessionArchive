import os
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError

API_ID = "22603992"
API_HASH = "78e2d35ead5467e121674e9795316d4d"
SESSION_FILE = "session.txt"

# Загружаем сессию из файла (если есть)
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r", encoding="utf-8") as file:
        session_str = file.read().strip()
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    print("🔄 Используем сохранённую сессию...", flush=True)
else:
    client = TelegramClient(StringSession(), API_ID, API_HASH)

async def main():
    await client.connect()
    print("✅ Клиент подключен!", flush=True)

    if not await client.is_user_authorized():
        phone = input("📱 Введите номер телефона: ").strip()
        sent_code = await client.send_code_request(phone)

        code = input("🔢 Введите код из Telegram: ").strip()
        try:
            print("⏳ Пытаемся войти без 2FA...", flush=True)
            await client.sign_in(phone=phone, code=code, phone_code_hash=sent_code.phone_code_hash)
            print("✅ Успешный вход без 2FA!", flush=True)
        except SessionPasswordNeededError:
            print("⚠️ Требуется ввод пароля 2FA!", flush=True)
            password = input("🔑 Введите пароль 2FA: ").strip()

            try:
                # Используем `asyncio.wait_for()`, чтобы задать тайм-аут на вход с 2FA
                await asyncio.wait_for(client.sign_in(password=password), timeout=10)
                print("✅ Успешный вход с 2FA!", flush=True)
            except PasswordHashInvalidError:
                print("❌ Ошибка: неверный пароль 2FA!", flush=True)
                return
            except asyncio.TimeoutError:
                print("❌ Ошибка: Telegram не ответил вовремя! Попробуйте позже.", flush=True)
                return
            except Exception as e:
                print(f"❌ Ошибка входа с 2FA: {e}", flush=True)
                return

        if client.session.save():
            try:
                with open(SESSION_FILE, "w", encoding="utf-8") as file:
                    file.write(client.session.save())
                print("\n✅ Авторизация успешна! Сессия сохранена в session.txt", flush=True)
            except Exception as e:
                print(f"❌ Ошибка сохранения сессии в файл: {e}", flush=True)
        else:
            print("❌ Ошибка: сессия не была корректно создана.", flush=True)

        # ✅ Гарантированное сохранение сессии в файл
        session_str = client.session.save()
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as file:
                file.write(session_str)
            print("\n✅ Авторизация успешна! Сессия сохранена.", flush=True)
        except Exception as e:
            print(f"❌ Ошибка сохранения сессии в файл: {e}", flush=True)

    else:
        print("\n✅ Вы уже авторизованы!", flush=True)

    # Выводим информацию о пользователе
    me = await client.get_me()
    print(f"\n👤 Вы вошли как: {me.first_name} (@{me.username})", flush=True)

with client:
    client.loop.run_until_complete(main())
