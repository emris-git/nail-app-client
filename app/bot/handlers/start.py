from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.client_api import ClientApi, ClientApiError
from app.config import get_settings

router = Router()


def _main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Каталог мастеров", callback_data="menu:catalog")],
            [InlineKeyboardButton(text="Избранное", callback_data="menu:favorites")],
            [InlineKeyboardButton(text="Мои записи", callback_data="menu:bookings")],
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.from_user is None:
        return
    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1] if len(parts) > 1 else ""

    if payload.startswith("master_"):
        slug = payload.removeprefix("master_")
        settings = get_settings()
        api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
        try:
            master = await api.get_master(message.from_user.id, slug)
            services = await api.list_services(message.from_user.id, slug)
        except ClientApiError as e:
            await message.answer(f"Ошибка API: {e}")
            return
        finally:
            await api.aclose()

        if not services:
            await message.answer("У мастера пока нет услуг для записи.")
            return

        # same callback schema as in catalog: master -> service selection
        from .catalog import _services_keyboard  # local import to avoid circular dependency

        await message.answer(
            f"Запись к мастеру <b>{master['display_name']}</b>\nВыберите услугу:",
            reply_markup=_services_keyboard(slug, services),
        )
        return

    await message.answer(
        "Привет! Здесь можно выбрать мастера, посмотреть услуги и записаться.\n\nВыберите действие:",
        reply_markup=_main_menu(),
    )

