from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.client_api import ClientApi, ClientApiError
from app.config import get_settings

from ..state import BookingFlow

router = Router()


def _masters_keyboard(masters: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for m in masters[:30]:
        rows.append([InlineKeyboardButton(text=m["display_name"], callback_data=f"master:{m['slug']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Нет мастеров", callback_data="noop")]])


def _services_keyboard(master_slug: str, services: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for s in services[:30]:
        label = f"{s['name']} — {int(s['price'])}, {s['duration_minutes']} мин"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"service:{master_slug}:{s['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _slots_keyboard(master_slug: str, service_id: int, slots: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for sl in slots[:40]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{sl['date']} {sl['time']}",
                    callback_data=f"slot:{master_slug}:{service_id}:{sl['date']}T{sl['time']}:00",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "menu:catalog")
async def menu_catalog(cb: CallbackQuery) -> None:
    await cb.answer()
    if cb.message is None:
        return
    settings = get_settings()
    api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
    try:
        masters = await api.list_masters(cb.from_user.id)
    except ClientApiError as e:
        await cb.message.answer(f"Ошибка API: {e}")
        return
    finally:
        await api.aclose()

    await cb.message.answer("Выберите мастера:", reply_markup=_masters_keyboard(masters))


@router.callback_query(F.data == "menu:favorites")
async def menu_favorites(cb: CallbackQuery) -> None:
    await cb.answer()
    if cb.message is None:
        return
    settings = get_settings()
    api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
    try:
        favs = await api.list_favorites(cb.from_user.id)
    except ClientApiError as e:
        await cb.message.answer(f"Ошибка API: {e}")
        return
    finally:
        await api.aclose()

    if not favs:
        await cb.message.answer("Избранное пустое. Откройте каталог и добавьте мастера.")
        return
    masters = [{"display_name": f["display_name"], "slug": f["slug"]} for f in favs]
    await cb.message.answer("Избранные мастера:", reply_markup=_masters_keyboard(masters))


@router.callback_query(F.data.startswith("master:"))
async def choose_master(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    slug = cb.data.split(":", 1)[1]
    settings = get_settings()
    api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
    try:
        master = await api.get_master(cb.from_user.id, slug)
        services = await api.list_services(cb.from_user.id, slug)
    except ClientApiError as e:
        await cb.message.answer(f"Ошибка API: {e}")
        return
    finally:
        await api.aclose()

    await state.update_data(master_slug=slug, master=master)
    await state.set_state(BookingFlow.choosing_service)
    await cb.message.answer(
        f"Мастер: <b>{master['display_name']}</b>\nВыберите услугу:",
        reply_markup=_services_keyboard(slug, services),
    )


@router.callback_query(F.data.startswith("service:"))
async def choose_service(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    _, master_slug, service_id_s = cb.data.split(":", 2)
    service_id = int(service_id_s)
    settings = get_settings()
    api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
    try:
        avail = await api.get_availability(cb.from_user.id, master_slug, service_id, days=14)
    except ClientApiError as e:
        await cb.message.answer(f"Ошибка API: {e}")
        return
    finally:
        await api.aclose()

    slots = avail.get("slots", [])
    if not slots:
        await cb.message.answer("Нет доступных слотов на ближайшие 14 дней.")
        return

    await state.update_data(master_slug=master_slug, service_id=service_id)
    await state.set_state(BookingFlow.choosing_slot)
    await cb.message.answer("Выберите слот:", reply_markup=_slots_keyboard(master_slug, service_id, slots))


@router.callback_query(F.data.startswith("slot:"))
async def choose_slot(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    if cb.message is None or cb.data is None:
        return
    _, master_slug, service_id_s, start_at_iso = cb.data.split(":", 3)
    service_id = int(service_id_s)

    data = await state.get_data()
    master = data.get("master") or {}
    tz_name = master.get("timezone")
    if not tz_name:
        await cb.message.answer("Не удалось определить таймзону мастера. Начните заново: /start")
        await state.clear()
        return

    # start_at_iso comes as 'YYYY-MM-DDTHH:MM:SS'
    naive = datetime.fromisoformat(start_at_iso)
    start_at = naive.replace(tzinfo=ZoneInfo(tz_name)).isoformat()

    settings = get_settings()
    api = ClientApi(str(settings.client_api_base_url), settings.client_api_hmac_secret)
    try:
        booking = await api.create_booking(cb.from_user.id, master_slug, service_id, start_at)
    except ClientApiError as e:
        await cb.message.answer(f"Не получилось создать запись: {e}")
        return
    finally:
        await api.aclose()

    await state.clear()
    await cb.message.answer(
        "Запись создана!\n\n"
        f"ID: {booking['id']}\n"
        f"Начало: {booking['start_at']}\n"
        f"Конец: {booking['end_at']}\n"
    )

