from __future__ import annotations

from datetime import datetime, timedelta, time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from aiogram import Bot

from .database import get_session
from .models import Booking, BookingStatusEnum, User, Service
from .config import settings
from .notifications import notify_user_reminder

NIGHT_START = time(22, 0)  # 22:00
NIGHT_END = time(8, 0)     # 08:00


def _is_night(t: time) -> bool:
    """
    Чи час у 'нічному' інтервалі [22:00, 08:00).
    """
    # ніч через північ: 22:00–24:00 та 00:00–08:00
    return t >= NIGHT_START or t < NIGHT_END


async def _process_reminders(bot: Bot) -> None:
    """
    Шукає бронювання, яким треба надіслати нагадування
    за 24/12/4/2 години.
    """
    now = datetime.utcnow()

    with get_session() as db:
        await _send_reminders_for_delta(db, bot, now, 24, "reminder_24h_sent")
        await _send_reminders_for_delta(db, bot, now, 12, "reminder_12h_sent")
        await _send_reminders_for_delta(db, bot, now, 4, "reminder_4h_sent")
        await _send_reminders_for_delta(db, bot, now, 2, "reminder_2h_sent")


async def _send_reminders_for_delta(
    db: Session,
    bot: Bot,
    now: datetime,
    delta_hours: int,
    flag_attr: str,
) -> None:
    """
    Для кожного бронювання, до якого залишилось delta_hours,
    надсилає нагадування, якщо прапорець reminder_*_sent == False.

    Якщо час надсилання потрапляє в ніч (22:00–08:00),
    надсилаємо о 08:00 відповідного дня.
    """
    delta = timedelta(hours=delta_hours)
    window = timedelta(minutes=5)

    target_from = now + delta - window
    target_to = now + delta + window

    q = (
        db.query(Booking)
        .filter(
            Booking.status.in_([BookingStatusEnum.APPROVED, BookingStatusEnum.PENDING]),
            Booking.start_datetime >= target_from,
            Booking.start_datetime <= target_to,
        )
    )

    if flag_attr == "reminder_24h_sent":
        q = q.filter(Booking.reminder_24h_sent.is_(False))
    elif flag_attr == "reminder_12h_sent":
        q = q.filter(Booking.reminder_12h_sent.is_(False))
    elif flag_attr == "reminder_4h_sent":
        q = q.filter(Booking.reminder_4h_sent.is_(False))
    elif flag_attr == "reminder_2h_sent":
        q = q.filter(Booking.reminder_2h_sent.is_(False))

    bookings = q.all()

    for booking in bookings:
        user = db.query(User).filter(User.id == booking.user_id).one_or_none()
        service = db.query(Service).filter(Service.id == booking.service_id).one_or_none()
        if not user or not service:
            continue

        ideal_send_time = booking.start_datetime - timedelta(hours=delta_hours)
        send_time_local = ideal_send_time.time()

        # Якщо ідеальний час у ніч — переносимо на 08:00
        if _is_night(send_time_local):
            send_datetime = datetime.combine(
                ideal_send_time.date(),
                time(8, 0),
            )
            # відправляємо тільки якщо зараз уже >= 08:00 того дня
            if now < send_datetime:
                continue

        await notify_user_reminder(
            bot=bot,
            user_tg_id=user.telegram_id,
            booking=booking,
            service=service,
            hours_before=delta_hours,
        )

        if flag_attr == "reminder_24h_sent":
            booking.reminder_24h_sent = True
        elif flag_attr == "reminder_12h_sent":
            booking.reminder_12h_sent = True
        elif flag_attr == "reminder_4h_sent":
            booking.reminder_4h_sent = True
        elif flag_attr == "reminder_2h_sent":
            booking.reminder_2h_sent = True

        db.flush()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
    scheduler.add_job(
        _process_reminders,
        trigger=IntervalTrigger(minutes=1),
        args=[bot],
        id="reminders_job",
        replace_existing=True,
    )
    return scheduler
