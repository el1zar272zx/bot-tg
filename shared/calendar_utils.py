from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .models import Booking, Service, User
from .config import settings


def generate_ics_content(
    booking: Booking,
    service: Service,
    user: User,
    tz_name: Optional[str] = None,
) -> str:
    """
    Генерує вміст .ics-файлу для запису.
    iPhone/Google календарі розуміють цей формат.
    """

    # У реальному проді варто конвертувати час у локальний timezone.
    # Зараз вважаємо, що start_datetime вже в локальному часі або ок.
    start = booking.start_datetime
    end = booking.start_datetime + timedelta(minutes=booking.duration_minutes)

    # Якщо timezone не заданий – беремо з settings
    tz = tz_name or settings.TIMEZONE

    # Унікальний ідентифікатор події (можна будь-який, головне — стабільний рядок)
    uid = f"booking-{booking.id}@massage-salon"

    # Створюємо текст .ics (мінімально необхідні поля)
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MassageSalonBot//UA
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:{uid}
SUMMARY:{service.name}
DESCRIPTION:Клієнт: {user.full_name or ''}\\nТелефон: {user.phone or ''}\\nПослуга: {service.name}\\nТривалість: {booking.duration_minutes} хв.
DTSTART;TZID={tz}:{start.strftime("%Y%m%dT%H%M%S")}
DTEND;TZID={tz}:{end.strftime("%Y%m%dT%H%M%S")}
END:VEVENT
END:VCALENDAR
"""
    return ics
