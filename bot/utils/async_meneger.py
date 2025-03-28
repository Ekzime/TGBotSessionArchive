from telethon import TelegramClient
from telethon.sessions import StringSession
from config import settings
from contextlib import asynccontextmanager


@asynccontextmanager
async def get_telegram_client(session_string):
    client = TelegramClient(
        StringSession(session_string),
        settings.API_TELETHON_ID,
        settings.API_TELETHON_HASH,
    )
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()
