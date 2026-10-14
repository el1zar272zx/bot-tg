from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Завантажуємо змінні з .env
load_dotenv()


@dataclass
class Settings:
    # URL БД. За замовчуванням локальний SQLite-файл у корені проекту
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./massage_salon.db")

    # Виводити SQL-запити в консоль (true/false)
    SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"

    # Токени ботів (додаси пізніше)
    CLIENT_BOT_TOKEN: str | None = os.getenv("CLIENT_BOT_TOKEN")
    ADMIN_BOT_TOKEN: str | None = os.getenv("ADMIN_BOT_TOKEN")

    # Часовий пояс
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Kyiv")

    # Перший адмін (опціонально)
    OWNER_TELEGRAM_ID: int | None = (
        int(os.getenv("OWNER_TELEGRAM_ID")) if os.getenv("OWNER_TELEGRAM_ID") else None
    )


settings = Settings()
