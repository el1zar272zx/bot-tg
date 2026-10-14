from __future__ import annotations

from datetime import datetime, time, date
from typing import Optional

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Date,
    Time,
    ForeignKey,
    Boolean,
    Float,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    services: Mapped[list["Service"]] = relationship(
        "Service", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ServiceCategory id={self.id} name={self.name!r}>"


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("service_categories.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["ServiceCategory"] = relationship(
        "ServiceCategory", back_populates="services"
    )

    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="service", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("category_id", "name", name="uq_service_category_name"),
    )

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r} duration={self.duration_minutes} price={self.price}>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id}>"


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Admin id={self.id} tg={self.telegram_id} owner={self.is_owner}>"


class WorkDay(Base):
    __tablename__ = "work_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Дата робочого дня
    date: Mapped[date] = mapped_column(Date, nullable=False)
    # Місто: "zv" (Жовті Води) або "pk" (Пʼятихатки)
    city: Mapped[str] = mapped_column(String(16), nullable=False)

    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    is_day_off: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    time_slots: Mapped[list["TimeSlot"]] = relationship(
        "TimeSlot", back_populates="work_day", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("date", "city", name="uq_workday_date_city"),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkDay date={self.date} city={self.city} "
            f"start={self.start_time} end={self.end_time} day_off={self.is_day_off}>"
        )


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_days.id", ondelete="CASCADE"), nullable=False
    )

    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    work_day: Mapped["WorkDay"] = relationship("WorkDay", back_populates="time_slots")

    __table_args__ = (
        UniqueConstraint(
            "work_day_id", "start_time", name="uq_timeslot_workday_start_time"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TimeSlot id={self.id} "
            f"date={self.work_day.date if self.work_day else None} "
            f"{self.start_time}-{self.end_time} blocked={self.is_blocked}>"
        )


class BookingStatusEnum(str):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )

    # Місто, в якому виконується запис ("zv" або "pk")
    city: Mapped[str] = mapped_column(String(16), nullable=False)

    start_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=BookingStatusEnum.PENDING, nullable=False
    )
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Для нагадувань: щоб не надсилати двічі
    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_12h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_4h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_2h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="bookings")
    service: Mapped["Service"] = relationship("Service", back_populates="bookings")

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} user_id={self.user_id} "
            f"service_id={self.service_id} city={self.city} "
            f"start={self.start_datetime} status={self.status}>"
        )




    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} user_id={self.user_id} "
            f"service_id={self.service_id} start={self.start_datetime} "
            f"status={self.status}>"
        )


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value!r}>"
