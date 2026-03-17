from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BookingFlow(StatesGroup):
    choosing_service = State()
    choosing_slot = State()

