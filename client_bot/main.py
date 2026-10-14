from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand


from shared.config import settings
from shared.scheduler import setup_scheduler
from client_bot.handlers import setup_client_routers


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Почати"),
        BotCommand(command="/book", description="Записатися на послугу"),
    ]
    await bot.set_my_commands(commands)


async def main():
    if not settings.CLIENT_BOT_TOKEN:
        raise RuntimeError("CLIENT_BOT_TOKEN is not set in .env")

    bot = Bot(
        token=settings.CLIENT_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    dp = Dispatcher()

    # Підключаємо всі хендлери
    dp.include_router(setup_client_routers())

    # Налаштовуємо scheduler для нагадувань
    scheduler = setup_scheduler(bot)
    scheduler.start()

    await set_commands(bot)

    # Запускаємо бот
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
