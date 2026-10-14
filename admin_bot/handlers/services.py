from __future__ import annotations

from datetime import datetime, timedelta, date, time
from typing import Optional, List, Tuple

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from .models import (
    ServiceCategory,
    Service,
    User,
    Booking,
    BookingStatusEnum,
    Setting,
    Admin,
    WorkDay,
    TimeSlot,
)
from .config import settings


# ---------- ХЕЛПЕРИ ПО НАЛАШТУВАННЯХ ----------

def get_setting(db: Session, key: str) -> Optional[str]:
    setting = db.query(Setting).filter(Setting.key == key).one_or_none()
    return setting.value if setting else None


def set_setting(db: Session, key: str, value: str) -> None:
    setting = db.query(Setting).filter(Setting.key == key).one_or_none()
    if setting is None:
        setting = Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value


def get_card_details(db: Session) -> Tuple[str, str]:
    """
    Повертає (номер_картки, ПІБ_власника).
    Якщо не задані — повертає заглушки.
    """
    number = get_setting(db, "card_number") or "0000 0000 0000 0000"
    holder = get_setting(db, "card_holder") or "Імʼя Прізвище"
    return number, holder


def update_card_details(db: Session, number: str, holder: str) -> None:
    set_setting(db, "card_number", number)
    set_setting(db, "card_holder", holder)


# ---------- КОРИСТУВАЧІ / АДМІНИ ----------

def get_or_create_user(
    db: Session, telegram_id: int, full_name: Optional[str] = None, phone: Optional[str] = None
) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, full_name=full_name, phone=phone)
        db.add(user)
        db.flush()
    else:
        # оновлюємо ім'я/телефон, якщо передані і змінились
        changed = False
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if phone and user.phone != phone:
            user.phone = phone
            changed = True
        if changed:
            db.flush()
    return user


def is_admin(db: Session, telegram_id: int) -> bool:
    return db.query(Admin).filter(Admin.telegram_id == telegram_id).count() > 0


def add_admin(db: Session, telegram_id: int, is_owner: bool = False) -> Admin:
    admin = db.query(Admin).filter(Admin.telegram_id == telegram_id).one_or_none()
    if admin is None:
        admin = Admin(telegram_id=telegram_id, is_owner=is_owner)
        db.add(admin)
        db.flush()
    return admin


def remove_admin(db: Session, telegram_id: int) -> bool:
    admin = db.query(Admin).filter(Admin.telegram_id == telegram_id).one_or_none()
    if admin is None:
        return False
    db.delete(admin)
    return True


def get_all_admins(db: Session) -> List[Admin]:
    return db.query(Admin).all()


# ---------- КАТЕГОРІЇ ТА ПОСЛУГИ ----------

def get_categories_with_services(db: Session) -> List[ServiceCategory]:
    """
    Отримати всі категорії з активними послугами.
    """
    # Ліниве завантаження services, але ми потім при виведенні просто ітеруємось.
    return (
        db.query(ServiceCategory)
        .order_by(ServiceCategory.id)
        .all()
    )


def get_services_by_category(db: Session, category_id: int) -> List[Service]:
    return (
        db.query(Service)
        .filter(Service.category_id == category_id, Service.is_active.is_(True))
        .order_by(Service.id)
        .all()
    )


def get_service(db: Session, service_id: int) -> Optional[Service]:
    return db.query(Service).filter(Service.id == service_id, Service.is_active.is_(True)).one_or_none()


def create_service(
    db: Session,
    category_id: int,
    name: str,
    duration_minutes: int,
    price: Optional[float],
    description: Optional[str] = None,
) -> Service:
    service = Service(
        category_id=category_id,
        name=name,
        duration_minutes=duration_minutes,
        price=price,
        description=description,
        is_active=True,
    )
    db.add(service)
    db.flush()
    return service


def update_service(
    db: Session,
    service_id: int,
    name: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    price: Optional[float] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[Service]:
    service = db.query(Service).filter(Service.id == service_id).one_or_none()
    if not service:
        return None
    if name is not None:
        service.name = name
    if duration_minutes is not None:
        service.duration_minutes = duration_minutes
    if price is not None or price is None:
        # дозволяємо скидати ціну в None
        service.price = price
    if description is not None:
        service.description = description
    if is_active is not None:
        service.is_active = is_active
    db.flush()
    return service


def delete_service(db: Session, service_id: int) -> bool:
    service = db.query(Service).filter(Service.id == service_id).one_or_none()
    if not service:
        return False
    db.delete(service)
    return True


def create_category(db: Session, name: str) -> ServiceCategory:
    cat = ServiceCategory(name=name)
    db.add(cat)
    db.flush()
    return cat


def rename_category(db: Session, category_id: int, new_name: str) -> Optional[ServiceCategory]:
    cat = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).one_or_none()
    if not cat:
        return None
    cat.name = new_name
    db.flush()
    return cat


def delete_category(db: Session, category_id: int) -> bool:
    cat = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).one_or_none()
    if not cat:
        return False
    db.delete(cat)
    return True


# ---------- РОЗКЛАД ----------

def set_work_day(
    db: Session,
    day: date,
    start: Optional[time],
    end: Optional[time],
    is_day_off: bool,
) -> WorkDay:
    """
    Встановлює (або оновлює) робочий день:
    - якщо is_day_off=True — день вихідний;
    - якщо False — задаємо start/end (можуть бути None, але зазвичай не треба).
    """
    wd = db.query(WorkDay).filter(WorkDay.date == day).one_or_none()
    if wd is None:
        wd = WorkDay(date=day)
        db.add(wd)
    wd.start_time = start
    wd.end_time = end
    wd.is_day_off = is_day_off
    db.flush()
    return wd


def block_timeslot(
    db: Session,
    day: date,
    start: time,
    end: time,
    blocked: bool = True,
) -> TimeSlot:
    """
    Блокує або розблоковує окремий timeslot у певний день.
    Якщо слоту немає — створюємо.
    """
    wd = db.query(WorkDay).filter(WorkDay.date == day).one_or_none()
    if wd is None:
        wd = WorkDay(date=day, start_time=None, end_time=None, is_day_off=False)
        db.add(wd)
        db.flush()

    ts = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.work_day_id == wd.id,
            TimeSlot.start_time == start,
        )
        .one_or_none()
    )
    if ts is None:
        ts = TimeSlot(
            work_day_id=wd.id,
            start_time=start,
            end_time=end,
            is_blocked=blocked,
        )
        db.add(ts)
    else:
        ts.end_time = end
        ts.is_blocked = blocked
    db.flush()
    return ts


def get_workday(db: Session, day: date) -> Optional[WorkDay]:
    return db.query(WorkDay).filter(WorkDay.date == day).one_or_none()


def get_blocked_timeslots(db: Session, day: date) -> List[TimeSlot]:
    wd = get_workday(db, day)
    if not wd:
        return []
    return (
        db.query(TimeSlot)
        .filter(TimeSlot.work_day_id == wd.id, TimeSlot.is_blocked.is_(True))
        .all()
    )


# ---------- БРОНЮВАННЯ (СЛОТИ) ----------

def _get_end_time(start: datetime, duration_minutes: int) -> datetime:
    return start + timedelta(minutes=duration_minutes)


def _booking_intervals_overlap(
    start1: datetime, end1: datetime, start2: datetime, end2: datetime
) -> bool:
    """
    Перевірка перетину інтервалів.
    """
    return start1 < end2 and start2 < end1


def is_slot_available(
    db: Session,
    service: Service,
    start_dt: datetime,
) -> bool:
    """
    Перевіряє, чи вільний слот для даної послуги на вказаний час.
    Перевірки:
    - день не вихідний;
    - входить у робочий діапазон;
    - не попадає в заблоковані timeslots;
    - немає інших бронювань, що перетинаються з цим інтервалом.
    """
    day = start_dt.date()
    end_dt = _get_end_time(start_dt, service.duration_minutes)

    # Робочий день
    wd = get_workday(db, day)
    if not wd or wd.is_day_off:
        return False

    # Перевірка, що час у загальних робочих годинах
    if wd.start_time and wd.end_time:
        if not (wd.start_time <= start_dt.time() < wd.end_time):
            return False
        if not (wd.start_time < end_dt.time() <= wd.end_time):
            return False

    # Перевірка блокованих timeslots
    blocked_slots = get_blocked_timeslots(db, day)
    for ts in blocked_slots:
        slot_start = datetime.combine(day, ts.start_time)
        slot_end = datetime.combine(day, ts.end_time)
        if _booking_intervals_overlap(start_dt, end_dt, slot_start, slot_end):
            return False

    # Перевірка інших бронювань (approved + pending)
    overlaps = (
        db.query(Booking)
        .filter(
            Booking.status.in_([BookingStatusEnum.PENDING, BookingStatusEnum.APPROVED]),
            func.date(Booking.start_datetime) == day,
        )
        .all()
    )
    for b in overlaps:
        b_start = b.start_datetime
        b_end = _get_end_time(b.start_datetime, b.duration_minutes)
        if _booking_intervals_overlap(start_dt, end_dt, b_start, b_end):
            return False

    return True


def create_booking(
    db: Session,
    user: User,
    service: Service,
    start_dt: datetime,
    payment_method: str,
) -> Optional[Booking]:
    """
    Створює бронювання, якщо слот вільний.
    Повертає Booking або None, якщо слот зайнятий/недоступний.
    """
    if not is_slot_available(db, service, start_dt):
        return None

    booking = Booking(
        user_id=user.id,
        service_id=service.id,
        start_datetime=start_dt,
        duration_minutes=service.duration_minutes,
        price=service.price,
        payment_method=payment_method,
        status=BookingStatusEnum.PENDING,
    )
    db.add(booking)
    db.flush()
    return booking


def get_user_future_bookings(
    db: Session,
    user: User,
    now: Optional[datetime] = None,
) -> List[Booking]:
    if now is None:
        now = datetime.utcnow()
    return (
        db.query(Booking)
        .filter(
            Booking.user_id == user.id,
            Booking.start_datetime >= now,
            Booking.status.in_(
                [
                    BookingStatusEnum.PENDING,
                    BookingStatusEnum.APPROVED,
                ]
            ),
        )
        .order_by(Booking.start_datetime)
        .all()
    )


def cancel_booking(
    db: Session,
    booking_id: int,
    initiated_by_admin: bool,
    reason: Optional[str] = None,
) -> Optional[Booking]:
    """
    Скасовує запис (клієнтом чи адміном).
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).one_or_none()
    if not booking:
        return None

    if booking.status in [BookingStatusEnum.CANCELED, BookingStatusEnum.REJECTED]:
        return booking

    booking.status = BookingStatusEnum.CANCELED
    if reason:
        booking.cancel_reason = reason
    db.flush()
    return booking


def change_booking_status(
    db: Session,
    booking_id: int,
    new_status: str,
    reason: Optional[str] = None,
) -> Optional[Booking]:
    """
    Використовується адміном для approve/reject.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).one_or_none()
    if not booking:
        return None

    if new_status not in (
        BookingStatusEnum.APPROVED,
        BookingStatusEnum.REJECTED,
        BookingStatusEnum.PENDING,
    ):
        raise ValueError("Invalid booking status")

    booking.status = new_status
    if reason:
        booking.cancel_reason = reason
    db.flush()
    return booking


def get_new_bookings(db: Session) -> List[Booking]:
    """
    Всі нові (pending) бронювання, відсортовані за часом.
    """
    return (
        db.query(Booking)
        .filter(Booking.status == BookingStatusEnum.PENDING)
        .order_by(Booking.start_datetime)
        .all()
    )


def get_bookings_for_period(
    db: Session,
    start: datetime,
    end: datetime,
) -> List[Booking]:
    """
    Для адмінського перегляду: бронювання в заданому періоді.
    """
    return (
        db.query(Booking)
        .filter(
            Booking.start_datetime >= start,
            Booking.start_datetime < end,
        )
        .order_by(Booking.start_datetime)
        .all()
    )
