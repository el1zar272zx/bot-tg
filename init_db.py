from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from shared.database import init_db as create_all, get_session
from shared.models import (
    ServiceCategory,
    Service,
    Setting,
    Admin,
)
from shared.config import settings


def get_or_create_category(db: Session, name: str) -> ServiceCategory:
    category = db.query(ServiceCategory).filter_by(name=name).one_or_none()
    if category is None:
        category = ServiceCategory(name=name)
        db.add(category)
        db.flush()
    return category


def add_initial_services(db: Session) -> None:
    cat_manual = get_or_create_category(db, "Ручні масажі")
    cat_hardware_massage = get_or_create_category(db, "Апаратні масажі")
    cat_injection = get_or_create_category(db, "Косметологія інʼєкційна")
    cat_hardware_cosm = get_or_create_category(db, "Апаратна косметологія")

    existing_services = {
        (s.category_id, s.name)
        for s in db.query(Service).all()
    }

    new_services: list[Service] = []

    def add_service(
        category: ServiceCategory,
        name: str,
        duration: int,
        price: Optional[float],
        description: Optional[str] = None,
    ):
        key = (category.id, name)
        if key in existing_services:
            return
        new_services.append(
            Service(
                category=category,
                name=name,
                duration_minutes=duration,
                price=price,
                description=description,
            )
        )

    # Ручні масажі
    add_service(
        cat_manual,
        "Ручний масаж спини",
        30,
        250,
        "спина + передпліччя + криж + грудна клітка або голова",
    )
    add_service(cat_manual, "Ручний масаж тіла", 60, 400)
    add_service(cat_manual, "Ручний масаж", 90, 600)
    add_service(cat_manual, "Масаж обличчя ручний + маска", 30, 300)
    add_service(cat_manual, "Реабілітація вдома", 60, 450)

    # Апаратні масажі
    add_service(cat_hardware_massage, "Пресотерапія 30 хв", 30, 250)
    add_service(cat_hardware_massage, "Пресотерапія 60 хв", 60, 400)

    add_service(cat_hardware_massage, "Апаратний масаж 30 хв", 30, 200)
    add_service(cat_hardware_massage, "Апаратний масаж 60 хв", 60, 400)

    add_service(cat_hardware_massage, "Роліковакуумний масаж 60 хв", 60, 300)

    add_service(cat_hardware_massage, "RF-ліфтинг 30 хв", 30, 200)
    add_service(cat_hardware_massage, "RF-ліфтинг 60 хв", 60, 300)
    add_service(cat_hardware_massage, "RF-ліфтинг 90 хв", 90, 500)

    add_service(cat_hardware_massage, "Ліполіз 30 хв", 30, 200)
    add_service(cat_hardware_massage, "Ліполіз 60 хв", 60, 300)

    add_service(cat_hardware_massage, "Кавітація 30 хв", 30, 200)
    add_service(cat_hardware_massage, "Кавітація 60 хв", 60, 300)

    add_service(cat_hardware_massage, "Апаратний масаж для обличчя 30 хв", 30, 250)

    # Косметологія інʼєкційна (без ціни)
    injection_services = [
        "Контурна пластика",
        "Ботулінотерапія",
        "Плазмотерапія",
        "Тредліфтінг",
        "Мезотерапія",
        "Чистка обличчя",
        "Ліпоредукція",
        "Інтимне відбілювання",
    ]
    for name in injection_services:
        add_service(cat_injection, name, 60, None)

    # Апаратна косметологія (без ціни)
    hardware_cosm_services = [
        "Морфіус8 — мікроголковий ліфтинг",
        "Інтимне омолодження",
        "Фотоомолодження",
        "Видалення пігментації / постакне",
        "RF-ліфтинг",
        "Вакуумний масаж",
    ]
    for name in hardware_cosm_services:
        add_service(cat_hardware_cosm, name, 60, None)

    if new_services:
        db.add_all(new_services)


def add_default_settings(db: Session) -> None:
    existing_settings = {s.key for s in db.query(Setting).all()}

    def set_default(key: str, value: str):
        if key in existing_settings:
            return
        db.add(Setting(key=key, value=value))

    set_default("card_number", "0000 0000 0000 0000")
    set_default("card_holder", "Імʼя Прізвище")
    set_default("timezone", settings.TIMEZONE)
    set_default("slot_step_minutes", "30")


def ensure_owner_admin(db: Session) -> None:
    if not settings.OWNER_TELEGRAM_ID:
        return

    owner = (
        db.query(Admin)
        .filter(Admin.telegram_id == settings.OWNER_TELEGRAM_ID)
        .one_or_none()
    )
    if owner is None:
        owner = Admin(telegram_id=settings.OWNER_TELEGRAM_ID, is_owner=True)
        db.add(owner)


def main() -> None:
    create_all()

    with get_session() as db:
        add_initial_services(db)
        add_default_settings(db)
        ensure_owner_admin(db)


if __name__ == "__main__":
    main()
