from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from database.db import AsyncSessionLocal
from database.crud import get_users_without_report_today
from config import REMINDER_TIME, TIMEZONE
import logging

logger = logging.getLogger(__name__)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    hour, minute = map(int, REMINDER_TIME.split(":"))

    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
        args=[bot],
        id="daily_reminder",
        replace_existing=True
    )

    logger.info(f"Scheduler set for {REMINDER_TIME} {TIMEZONE}")
    return scheduler


async def send_daily_reminders(bot: Bot):
    logger.info("Sending daily reminders...")
    async with AsyncSessionLocal() as session:
        users = await get_users_without_report_today(session)

    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                "⏰ Eslatma!\n\n"
                "📝 Bugun hali hisobot yubormagansiz.\n"
                "Iltimos, ish kuni yakunida hisobotingizni yuboring.\n\n"
                "Yuborish uchun: 📝 Hisobot yuborish"
            )
        except Exception as e:
            logger.warning(f"Could not send reminder to {user.telegram_id}: {e}")

    logger.info(f"Reminders sent to {len(users)} users")
