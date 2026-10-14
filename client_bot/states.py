from __future__ import annotations

from aiogram.fsm.state import StatesGroup, State


class BookingStates(StatesGroup):
    choosing_city = State()
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    choosing_payment = State()
    confirm = State()
