from __future__ import annotations

from aiogram.types import CallbackQuery, Message

from aiogram import Router, F
from aiogram.types import CallbackQuery

from shared.database import get_session
from shared.services import (
    get_or_create_user,
    get_user_future_bookings,
    cancel_booking,
    get_service,
    get_all_admins,
)
from client_bot.keyboards import my_bookings_kb, booking_actions_kb, main_menu_kb
from shared.notifications import notify_admins_about_cancellation
from shared.config import settings

router = Router(name="client_my_bookings")


@router.callback_query(F.data == "menu_my_bookings")
async def show_my_bookings(callback: CallbackQuery):
    with get_session() as db:
        user = get_or_create_user(db, telegram_id=callback.from_user.id)
        bookings = get_user_future_bookings(db, user)

    if not bookings:
        await callback.message.edit_text(
            "У вас немає майбутніх записів.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "Ваші майбутні записи:",
        reply_markup=my_bookings_kb(bookings),
    )
    await callback.answer()


@router.callback_query(F.data == "back_my_bookings")
async def back_my_bookings(callback: CallbackQuery):
    await show_my_bookings(callback)


@router.callback_query(F.data.startswith("myb_"))
async def my_booking_details(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[1])

    with get_session() as db:
        user = get_or_create_user(db, telegram_id=callback.from_user.id)
        # Переконуємось, що цей запис належить користувачу
        bookings = get_user_future_bookings(db, user)
        booking = next((b for b in bookings if b.id == booking_id), None)
        if not booking:
            await callback.answer("Запис не знайдено або він уже неактуальний.", show_alert=True)
            return
        service = get_service(db, booking.service_id)

    text = (
        f"Запис ID {booking.id}\n\n"
        f"Послуга: {service.name if service else booking.service_id}\n"
        f"Дата та час: {booking.start_datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"Тривалість: {booking.duration_minutes} хв\n"
        f"Статус: {booking.status}\n"
    )
    if booking.price is not None:
        text += f"Ціна: {booking.price:.0f} грн\n"

    await callback.message.edit_text(
        text,
        reply_markup=booking_actions_kb(booking_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_my_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[1])

    with get_session() as db:
        user = get_or_create_user(db, telegram_id=callback.from_user.id)
        bookings = get_user_future_bookings(db, user)
        booking = next((b for b in bookings if b.id == booking_id), None)
        if not booking:
            await callback.answer("Запис не знайдено або він уже неактуальний.", show_alert=True)
            return

        booking = cancel_booking(
            db=db,
            booking_id=booking_id,
            initiated_by_admin=False,
            reason="Скасовано клієнтом",
        )
        service = get_service(db, booking.service_id) if booking else None
        admins = get_all_admins(db)

    if not booking:
        await callback.answer("Не вдалося скасувати запис.", show_alert=True)
        return

    await callback.message.edit_text(
        "Ваш запис скасовано.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer("Запис скасовано.")

    # Сповіщаємо адмінів
    if admins and service:
        try:
            await notify_admins_about_cancellation(
                bot=callback.bot,
                admins=admins,
                booking=booking,
                user=user,
                service=service,
                by_admin=False,
            )
        except Exception:
            pass

        from aiogram.types import Message

@router.message(F.text == "/debug_bookings")
async def debug_bookings(message: Message):
    from datetime import datetime
    with get_session() as db:
        user = get_or_create_user(db, telegram_id=message.from_user.id)
        bookings = get_user_future_bookings(db, user, now=datetime(2020, 1, 1))  # спеціально з дуже старою датою

    if not bookings:
        await message.answer("DEBUG: для вас не знайдено жодного запису.")
        return

    text = "DEBUG: ваші записи:\n\n"
    for b in bookings:
        text += (
            f"ID {b.id} | {b.start_datetime.strftime('%d.%m.%Y %H:%M')} | "
            f"status={b.status} | user_id={b.user_id}\n"
        )
    await message.answer(text)

@router.message(F.text == "📂 Мої записи")
async def msg_my_bookings(message: Message):
    with get_session() as db:
        user = get_or_create_user(db, telegram_id=message.from_user.id)
        bookings = get_user_future_bookings(db, user)

    if not bookings:
        await message.answer(
            "У вас немає майбутніх записів.",
        )
        return

    await message.answer(
        "Ваші майбутні записи:",
        reply_markup=my_bookings_kb(bookings),
    )


@router.message(F.text == "/mybookings")
async def cmd_my_bookings(message: Message):
    await msg_my_bookings(message)
