import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/construction_bot")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SUPER_ADMIN_IDS = list(map(int, os.getenv("SUPER_ADMIN_IDS", "123456789").split(",")))

# Reminder time (HH:MM)
REMINDER_TIME = os.getenv("REMINDER_TIME", "17:00")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

# File upload
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10MB
MEDIA_DIR = "media"
