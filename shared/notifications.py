from __future__ import annotations

from typing import Iterable, Optional

from aiogram import Bot

from .models import Booking, User, Admin, Service
from .services import get_all_admins


async def notify_user_about_booking(
    bot: Bot,
    user_tg_id: int,
    booking: Booking,
    service: Service,
    prefix: str = "",
) -> None:
    """
    Повідомлення клієнту про створення/оновлення/скасування запису.
    prefix можна використати типу "✅ " або "❌ ".
    """
    text = (
        f"{prefix}Ваш запис:\n\n"
        f"Послуга: {service.name}\n"
        f"Дата та час: {booking.start_datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"Тривалість: {booking.duration_minutes} хв\n"
        f"Статус: {booking.status}\n"
    )
    if booking.price is not None:
        text += f"Ціна: {booking.price:.0f} грн\n"
    if booking.payment_method == "card":
        text += "Оплата: картка\n"
    else:
        text += "Оплата: готівка\n"

    if booking.cancel_reason:
        text += f"\nПричина: {booking.cancel_reason}"

    await bot.send_message(chat_id=user_tg_id, text=text)


async def notify_admins_about_new_booking(
    bot: Bot,
    admins: Iterable[Admin],
    booking: Booking,
    user: User,
    service: Service,
) -> None:
    """
    Оповіщення всіх адмінів про новий запис.
    """
    text = (
        "🆕 Новий запис\n\n"
        f"Клієнт: {user.full_name or ''} (tg_id={user.telegram_id})\n"
        f"Телефон: {user.phone or '-'}\n"
        f"Послуга: {service.name}\n"
        f"Дата та час: {booking.start_datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"Спосіб оплати: {'Картка' if booking.payment_method == 'card' else 'Готівка'}\n"
        f"Статус: {booking.status}\n"
        f"ID запису: {booking.id}\n"
    )
    for admin in admins:
        try:
            await bot.send_message(chat_id=admin.telegram_id, text=text)
        except Exception:
            # Не падаємо, якщо комусь не доставилось
            continue


async def notify_admins_about_cancellation(
    bot: Bot,
    admins: Iterable[Admin],
    booking: Booking,
    user: User,
    service: Service,
    by_admin: bool,
) -> None:
    """
    Оповіщення адмінів про скасування запису.
    """
    who = "адміном" if by_admin else "клієнтом"
    text = (
        "❌ Скасування запису\n\n"
        f"Скасовано: {who}\n"
        f"Клієнт: {user.full_name or ''} (tg_id={user.telegram_id})\n"
        f"Послуга: {service.name}\n"
        f"Дата та час: {booking.start_datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"ID запису: {booking.id}\n"
    )
    if booking.cancel_reason:
        text += f"Причина: {booking.cancel_reason}"

    for admin in admins:
        try:
            await bot.send_message(chat_id=admin.telegram_id, text=text)
        except Exception:
            continue


async def notify_user_reminder(
    bot: Bot,
    user_tg_id: int,
    booking: Booking,
    service: Service,
    hours_before: int,
) -> None:
    """
    Нагадування клієнту перед записом (за 24 або 2 години).
    """
    text = (
        f"Нагадування!\n\n"
        f"Через {hours_before} год "
        f"у вас запис на послугу: {service.name}\n"
        f"Дата та час: {booking.start_datetime.strftime('%d.%m.%Y %H:%M')}\n"
    )
    await bot.send_message(chat_id=user_tg_id, text=text)
