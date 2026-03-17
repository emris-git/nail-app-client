from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.config import get_settings

from .handlers import bookings, catalog, start


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    settings = get_settings()
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    storage: BaseStorage = MemoryStorage()
    if settings.redis_url:
        storage = RedisStorage(redis=Redis.from_url(settings.redis_url))
    dp = Dispatcher(storage=storage)

    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(bookings.router)

    return bot, dp

