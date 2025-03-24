from aiogram import Router
from bot.handlers.auth_handlers import router as auth_router
from bot.handlers.give_tg_handler import router as give_tg_router
from bot.handlers.take_tg_handler import router as take_rg_router
from bot.handlers.start_handler import router as start_router
from bot.handlers.view_tg_handdler import router as view_tg_router
from bot.handlers.info_handlers import router as info_chat_router
from bot.middlewares.auth_middleware import AuthMiddleware
from bot.callbacks.callbacks import router as callback_router


root_router = Router()

root_router.message.middleware(AuthMiddleware())

root_router.include_router(auth_router)
root_router.include_router(start_router)
root_router.include_router(give_tg_router)
root_router.include_router(take_rg_router)
root_router.include_router(view_tg_router)
root_router.include_router(info_chat_router)

root_router.include_router(callback_router)
