from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.client_api import ClientApi, ClientApiError
from app.config import get_settings

router = Router()


def _bookings_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for it in items[:20]:
        bid = it["id"]
        status = it["status"]
        start_at = str(it["start_at"])
        master = it["master"]["display_name"]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{master} • {start_at} • {status}",
                    callback_data=f"booking:{bid}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Пусто", callback_data="noop")]])


@router.callback_query(F.data == "menu:bookings")
async def menu_bookings(cb: CallbackQuery) -> None:
    await cb.answer()
    if cb.message is None:
        return
    settings = get_settings()
    api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
    try:
        data = await api.my_bookings(cb.from_user.id)
    except ClientApiError as e:
        await cb.message.answer(f"Ошибка API: {e}")
        return
    finally:
        await api.aclose()

    items = data.get("items", [])
    await cb.message.answer("Ваши записи:", reply_markup=_bookings_keyboard(items))


@router.callback_query(F.data.startswith("booking:"))
async def booking_actions(cb: CallbackQuery) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    booking_id = int(cb.data.split(":", 1)[1])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отменить запись", callback_data=f"cancel:{booking_id}")],
        ]
    )
    await cb.message.answer(f"Запись #{booking_id}", reply_markup=kb)


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_booking(cb: CallbackQuery) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    booking_id = int(cb.data.split(":", 1)[1])
    settings = get_settings()
    api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
    try:
        await api.cancel_booking(cb.from_user.id, booking_id)
    except ClientApiError as e:
        await cb.message.answer(f"Ошибка отмены: {e}")
        return
    finally:
        await api.aclose()

    await cb.message.answer("Отменено.")

