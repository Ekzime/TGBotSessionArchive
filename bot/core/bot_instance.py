from aiogram import Bot
import os
from config import settings

token = settings.TELEGRAM_BOT_API
bot = Bot(token=token)
