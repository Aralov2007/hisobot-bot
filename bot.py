import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import user_router, admin_router, auth_router, common_router
from middlewares.auth_middleware import AuthMiddleware
from utils.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    # Initialize DB
    await init_db()
    logger.info("Database initialized")

    # Storage (Redis olib tashlandi)
    storage = MemoryStorage()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # Middlewares
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Routers
    dp.include_router(auth_router)
    dp.include_router(common_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)

    # Scheduler (daily reminders)
    scheduler = setup_scheduler(bot)
    scheduler.start()

    logger.info("Bot started!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())