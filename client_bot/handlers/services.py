from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from shared.database import get_session
from shared.services import (
    get_categories_with_services,
    get_services_by_category,
    get_service,
)
from client_bot.keyboards import (
    main_menu_kb,
    categories_kb,
    services_kb,
    main_reply_kb,
)

router = Router(name="client_services")


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "Вітаю! Це бот салону масажу та косметології.\n\n"
        "Нижче є меню з основними діями:\n"
        "📅 Записатися\n"
        "🧾 Послуги\n"
        "📂 Мої записи",
        reply_markup=main_reply_kb(),
    )


@router.message(F.text == "🧾 Послуги")
async def msg_menu_services(message: Message):
    """
    Нижня кнопка '🧾 Послуги' — показує список категорій.
    """
    with get_session() as db:
        categories = get_categories_with_services(db)
    await message.answer(
        "Оберіть категорію послуг:",
        reply_markup=categories_kb(categories),
    )


@router.callback_query(F.data == "back_main")
async def back_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Головне меню:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_services")
async def show_categories(callback: CallbackQuery):
    """
    Кнопка з inline-меню 'Послуги' — теж показує список категорій.
    """
    with get_session() as db:
        categories = get_categories_with_services(db)
    await callback.message.edit_text(
        "Оберіть категорію послуг:",
        reply_markup=categories_kb(categories),
    )
    await callback.answer()


@router.callback_query(F.data == "back_categories")
async def back_to_categories(callback: CallbackQuery):
    with get_session() as db:
        categories = get_categories_with_services(db)
    await callback.message.edit_text(
        "Оберіть категорію послуг:",
        reply_markup=categories_kb(categories),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def show_services(callback: CallbackQuery):
    """
    Вибір категорії — показує список послуг цієї категорії.
    """
    category_id = int(callback.data.split("_")[1])
    with get_session() as db:
        services = get_services_by_category(db, category_id)
    if not services:
        await callback.answer("У цій категорії поки немає активних послуг.", show_alert=True)
        return
    await callback.message.edit_text(
        "Оберіть послугу:",
        reply_markup=services_kb(services, category_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("svc_"))
async def show_service_info(callback: CallbackQuery):
    """
    Користувач натиснув на конкретну послугу — показуємо інформацію.
    Для запису — окрема кнопка / команда (/book, '📅 Записатися').
    """
    service_id = int(callback.data.split("_")[1])
    with get_session() as db:
        service = get_service(db, service_id)

    if not service:
        await callback.answer("Послугу не знайдено.", show_alert=True)
        return

    text = (
        f"Послуга: {service.name}\n"
        f"Тривалість: {service.duration_minutes} хв\n"
    )
    if service.price is not None:
        text += f"Ціна: {service.price:.0f} грн\n"
    else:
        text += "Ціна уточнюється у адміністратора.\n"

    text += (
        "\nЩоб записатися, натисніть «📅 Записатися» внизу "
        "або скористайтесь командою /book."
    )

    await callback.message.edit_text(text)
    await callback.answer()
