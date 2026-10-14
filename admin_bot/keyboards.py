from __future__ import annotations

from datetime import date, timedelta, time
from typing import Iterable

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from shared.models import ServiceCategory, Service, Booking


# ---------- ГОЛОВНЕ МЕНЮ ----------

def main_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🧾 Послуги", callback_data="menu_services")],
        [InlineKeyboardButton(text="📅 Мої записи", callback_data="menu_my_bookings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ---------- КАТЕГОРІЇ / ПОСЛУГИ ----------

def categories_kb(categories: Iterable[ServiceCategory]) -> InlineKeyboardMarkup:
    rows = []
    for c in categories:
        rows.append(
            [InlineKeyboardButton(text=c.name, callback_data=f"cat_{c.id}")]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def services_kb(services: Iterable[Service], category_id: int) -> InlineKeyboardMarkup:
    rows = []
    for s in services:
        text = s.name
        if s.price is not None:
            text += f" — {s.price:.0f} грн"
        rows.append(
            [InlineKeyboardButton(text=text, callback_data=f"svc_{s.id}")]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- ВИБІР ДАТИ / ЧАСУ ----------

def dates_kb(days_ahead: int = 14) -> InlineKeyboardMarkup:
    """
    Клавіатура з найближчими днями (сьогодні + days_ahead).
    Дати у форматі callback_data: date_YYYY-MM-DD
    """
    today = date.today()
    rows = []
    row = []
    for i in range(days_ahead + 1):
        d = today + timedelta(days=i)
        btn = InlineKeyboardButton(text=d.strftime("%d.%m"), callback_data=f"date_{d.isoformat()}")
        row.append(btn)
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_services")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times_kb(times: list[time]) -> InlineKeyboardMarkup:
    """
    Список доступних часових слотів (формат callback: time_HH:MM).
    """
    rows = []
    row = []
    for t in times:
        text = t.strftime("%H:%M")
        row.append(InlineKeyboardButton(text=text, callback_data=f"time_{text}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_dates")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- СПОСІБ ОПЛАТИ ----------

def payment_method_kb() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="💵 Готівка", callback_data="pay_cash"),
            InlineKeyboardButton(text="💳 Картка", callback_data="pay_card"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_phone")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ---------- МОЇ ЗАПИСИ ----------

def my_bookings_kb(bookings: list[Booking]) -> InlineKeyboardMarkup:
    rows = []
    for b in bookings:
        dt_str = b.start_datetime.strftime("%d.%m %H:%M")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{dt_str} (ID {b.id})",
                    callback_data=f"myb_{b.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def booking_actions_kb(booking_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="❌ Скасувати запис", callback_data=f"cancel_{booking_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_my_bookings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
