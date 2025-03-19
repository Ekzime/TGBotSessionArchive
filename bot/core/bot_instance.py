from aiogram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_API = os.getenv("TELEGRAM_BOT_API")
bot = Bot(TELEGRAM_BOT_API)