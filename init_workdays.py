from __future__ import annotations

from datetime import date, time, timedelta

from shared.database import get_session
from shared.services import set_work_day


def main():
    today = date.today()
    days_ahead = 14  # скільки днів вперед зробити робочими

    with get_session() as db:
        for i in range(days_ahead + 1):
            d = today + timedelta(days=i)
            # Жовті Води ("zv")
            set_work_day(
                db=db,
                day=d,
                city="zv",          # Жовті Води
                start=time(10, 0),
                end=time(20, 0),
                is_day_off=False,
            )
            # Пʼятихатки ("pk")
            set_work_day(
                db=db,
                day=d,
                city="pk",          # Пʼятихатки
                start=time(10, 0),
                end=time(20, 0),
                is_day_off=False,
            )
        print(
            f"Створено/оновлено робочі дні з {today} по {today + timedelta(days=days_ahead)} "
            f"для міст 'zv' і 'pk'"
        )


if __name__ == "__main__":
    main()
