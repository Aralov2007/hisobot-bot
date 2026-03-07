from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any, Awaitable
from database.db import AsyncSessionLocal
from database.crud import get_user_by_telegram_id
from database.models import UserStatus


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        telegram_id = None

        if isinstance(event, Message):
            telegram_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            telegram_id = event.from_user.id

        if telegram_id:
            async with AsyncSessionLocal() as session:
                user = await get_user_by_telegram_id(session, telegram_id)
                data["db_user"] = user
                data["session"] = session

        return await handler(event, data)
