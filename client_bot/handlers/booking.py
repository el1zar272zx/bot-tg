from __future__ import annotations

from datetime import datetime, date, time, timedelta

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
)
from aiogram.fsm.context import FSMContext

from shared.database import get_session
from shared.services import (
    get_categories_with_services,
    get_services_by_category,
    get_service,
    get_or_create_user,
    create_booking,
    get_card_details,
    is_slot_available,
    get_workday,
)
from shared.calendar_utils import generate_ics_content
from client_bot.states import BookingStates
from client_bot.keyboards import (
    main_menu_kb,
    categories_kb,
    services_kb,
    dates_kb,
    times_kb,
    payment_method_kb,
    request_contact_kb,
    remove_reply_kb,
    confirm_booking_kb,
    cities_kb,
    main_reply_kb,
)

router = Router(name="client_booking")


# ---------- ХЕЛПЕРИ ДАТИ/ЧАСУ ----------

def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def _parse_time(time_str: str) -> time:
    return datetime.strptime(time_str, "%H:%M").time()


# ---------- СТАРТ ЗАПИСУ ----------

@router.message(F.text == "/book")
async def cmd_book(message: Message, state: FSMContext):
    """
    Старт сценарію запису.
    Прибираємо нижню клавіатуру та питаємо місто.
    """
    await state.clear()

    # Прибираємо нижню reply-клавіатуру
    await message.answer(
        "Починаємо запис...",
        reply_markup=remove_reply_kb(),
    )

    # Inline-кнопки вибору міста
    await message.answer(
        "Оберіть місто, де бажаєте пройти процедуру:",
        reply_markup=cities_kb(),
    )
    await state.set_state(BookingStates.choosing_city)


@router.message(F.text == "📅 Записатися")
async def msg_book(message: Message, state: FSMContext):
    await cmd_book(message, state)


# ---------- ВИБІР МІСТА / КАТЕГОРІЇ / ПОСЛУГИ ----------

@router.callback_query(BookingStates.choosing_city, F.data.in_(["city_zv", "city_pk"]))
async def booking_choose_city(callback: CallbackQuery, state: FSMContext):
    """
    Вибір міста для сценарію /book.
    Після вибору міста показуємо категорії послуг.
    """
    data = callback.data
    city_code = "zv" if data == "city_zv" else "pk"
    city_name = "Жовті Води" if city_code == "zv" else "Пʼятихатки"

    await state.update_data(city=city_code)

    # Показуємо категорії
    with get_session() as db:
        categories = get_categories_with_services(db)

    await callback.message.edit_text(
        f"Місто: {city_name}\n\nОберіть категорію послуг для запису:",
        reply_markup=categories_kb(categories),
    )
    await state.set_state(BookingStates.choosing_service)
    await callback.answer()


@router.callback_query(BookingStates.choosing_service, F.data.startswith("cat_"))
async def booking_choose_service_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    with get_session() as db:
        services = get_services_by_category(db, category_id)
    if not services:
        await callback.answer("У цій категорії немає активних послуг.", show_alert=True)
        return
    await callback.message.edit_text(
        "Оберіть послугу для запису:",
        reply_markup=services_kb(services, category_id),
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_service, F.data.startswith("svc_"))
async def booking_choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    await state.update_data(service_id=service_id)
    await callback.message.edit_text(
        "Оберіть дату:",
        reply_markup=dates_kb(),
    )
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()


# ---------- ВИБІР ДАТИ / ЧАСУ ----------

@router.callback_query(BookingStates.choosing_date, F.data.startswith("date_"))
async def booking_choose_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_", 1)[1]
    selected_date = _parse_date(date_str)
    data = await state.get_data()
    service_id = data.get("service_id")
    city = data.get("city")  # "zv" або "pk"

    if not city:
        await callback.answer("Не вказано місто. Спробуйте /book ще раз.", show_alert=True)
        await state.clear()
        await callback.message.edit_text(
            "Сталася помилка. Спробуйте /book ще раз.",
            reply_markup=main_menu_kb(),
        )
        return

    with get_session() as db:
        service = get_service(db, service_id)
        if not service:
            await callback.answer("Послугу не знайдено.", show_alert=True)
            await state.clear()
            await callback.message.edit_text(
                "Сталася помилка. Спробуйте /book ще раз.",
                reply_markup=main_menu_kb(),
            )
            return

        wd = get_workday(db, selected_date, city)
        if not wd or wd.is_day_off or not wd.start_time or not wd.end_time:
            await callback.answer("На цю дату немає робочого дня для цього міста.", show_alert=True)
            return

        step_minutes = 30  # крок між слотами
        times: list[time] = []
        current_dt = datetime.combine(selected_date, wd.start_time)
        end_dt = datetime.combine(selected_date, wd.end_time)

        while current_dt + timedelta(minutes=service.duration_minutes) <= end_dt:
            if is_slot_available(db, service, current_dt, city=city):
                times.append(current_dt.time())
            current_dt += timedelta(minutes=step_minutes)

    if not times:
        await callback.answer("На цю дату немає вільного часу.", show_alert=True)
        return

    await state.update_data(date=date_str)
    await callback.message.edit_text(
        f"Оберіть час для {selected_date.strftime('%d.%m.%Y')}:",
        reply_markup=times_kb(times),
    )
    await state.set_state(BookingStates.choosing_time)
    await callback.answer()


@router.callback_query(BookingStates.choosing_time, F.data.startswith("time_"))
async def booking_choose_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_", 1)[1]
    await state.update_data(time=time_str)
    await callback.message.edit_text(
        "Введіть, будь ласка, ваше імʼя:",
    )
    await state.set_state(BookingStates.entering_name)
    await callback.answer()


# ---------- ІМʼЯ / ТЕЛЕФОН ----------

@router.message(BookingStates.entering_name)
async def booking_enter_name(message: Message, state: FSMContext):
    full_name = (message.text or "").strip()
    if not full_name:
        await message.answer("Будь ласка, введіть ваше імʼя текстом.")
        return

    await state.update_data(full_name=full_name)

    with get_session() as db:
        user = get_or_create_user(
            db,
            telegram_id=message.from_user.id,
            full_name=full_name,
        )
        existing_phone = user.phone

    if existing_phone:
        await state.update_data(phone=existing_phone)
        await message.answer(
            f"Ваш збережений номер телефону: {existing_phone}",
            reply_markup=remove_reply_kb(),
        )
        await message.answer(
            "Оберіть спосіб оплати:",
            reply_markup=payment_method_kb(),
        )
        await state.set_state(BookingStates.choosing_payment)
    else:
        await message.answer(
            "Надішліть, будь ласка, ваш номер телефону.\n"
            "Найзручніше — натиснути кнопку нижче:",
            reply_markup=request_contact_kb(),
        )
        await state.set_state(BookingStates.entering_phone)


@router.message(BookingStates.entering_phone)
async def booking_enter_phone(message: Message, state: FSMContext):
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()

    if not phone:
        await message.answer(
            "Не вдалося отримати номер телефону. "
            "Спробуйте ще раз або надішліть контакт кнопкою.",
            reply_markup=request_contact_kb(),
        )
        return

    await state.update_data(phone=phone)

    await message.answer(
        "Дякую, номер збережено.",
        reply_markup=remove_reply_kb(),
    )

    await message.answer(
        "Оберіть спосіб оплати:",
        reply_markup=payment_method_kb(),
    )
    await state.set_state(BookingStates.choosing_payment)


# ---------- СПОСІБ ОПЛАТИ / ПІДТВЕРДЖЕННЯ ----------

@router.callback_query(BookingStates.choosing_payment, F.data.in_(["pay_cash", "pay_card"]))
async def booking_choose_payment(callback: CallbackQuery, state: FSMContext):
    pay_data = callback.data
    payment_method = "cash" if pay_data == "pay_cash" else "card"

    data = await state.get_data()
    service_id = data.get("service_id")
    date_str = data.get("date")
    time_str = data.get("time")
    full_name = data.get("full_name")
    phone = data.get("phone")

    selected_date = _parse_date(date_str)
    selected_time = _parse_time(time_str)
    start_dt = datetime.combine(selected_date, selected_time)

    with get_session() as db:
        service = get_service(db, service_id)
        if not service:
            await callback.answer("Послугу не знайдено.", show_alert=True)
            await state.clear()
            await callback.message.edit_text(
                "Сталася помилка. Спробуйте /book ще раз.",
                reply_markup=main_menu_kb(),
            )
            return

    await state.update_data(payment_method=payment_method)

    text = (
        "Перевірте, будь ласка, дані запису:\n\n"
        f"Послуга: {service.name}\n"
        f"Дата та час: {start_dt.strftime('%d.%m.%Y %H:%M')}\n"
        f"Тривалість: {service.duration_minutes} хв\n"
        f"Імʼя: {full_name}\n"
        f"Телефон: {phone}\n"
        f"Спосіб оплати: {'Картка' if payment_method == 'card' else 'Готівка'}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=confirm_booking_kb(),
    )
    await state.set_state(BookingStates.confirm)
    await callback.answer()


@router.callback_query(BookingStates.confirm, F.data == "cancel_booking_flow")
async def booking_flow_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Користувач відмінив запис на екрані підтвердження.
    """
    await state.clear()
    await callback.message.edit_text(
        "Запис скасовано.",
        reply_markup=main_menu_kb(),
    )
    # Повертаємо нижнє меню
    await callback.message.answer(
        "Повертаємось до головного меню.",
        reply_markup=main_reply_kb(),
    )
    await callback.answer()


@router.callback_query(BookingStates.confirm, F.data == "confirm_booking")
async def booking_flow_confirm(callback: CallbackQuery, state: FSMContext):
    """
    Користувач підтвердив запис — тут створюємо бронювання.
    """
    data = await state.get_data()
    service_id = data.get("service_id")
    date_str = data.get("date")
    time_str = data.get("time")
    full_name = data.get("full_name")
    phone = data.get("phone")
    payment_method = data.get("payment_method")
    city = data.get("city")

    if not city:
        await callback.answer("Не вказано місто. Спробуйте /book ще раз.", show_alert=True)
        await state.clear()
        await callback.message.edit_text(
            "Сталася помилка. Спробуйте /book ще раз.",
            reply_markup=main_menu_kb(),
        )
        return

    selected_date = _parse_date(date_str)
    selected_time = _parse_time(time_str)
    start_dt = datetime.combine(selected_date, selected_time)

    with get_session() as db:
        service = get_service(db, service_id)
        if not service:
            await callback.answer("Послугу не знайдено.", show_alert=True)
            await state.clear()
            await callback.message.edit_text(
                "Сталася помилка. Спробуйте /book ще раз.",
                reply_markup=main_menu_kb(),
            )
            return

        user = get_or_create_user(
            db,
            telegram_id=callback.from_user.id,
            full_name=full_name,
            phone=phone,
        )

        if not is_slot_available(db, service, start_dt, city=city):
            await callback.answer("На жаль, цей час уже зайнятий. Оберіть інший.", show_alert=True)
            await state.clear()
            await callback.message.edit_text(
                "Час недоступний. Спробуйте /book ще раз і виберіть інший слот.",
                reply_markup=main_menu_kb(),
            )
            return

        booking = create_booking(
            db=db,
            user=user,
            service=service,
            start_dt=start_dt,
            payment_method=payment_method,
            city=city,
        )

        if not booking:
            await callback.answer("Не вдалося створити запис. Спробуйте ще раз.", show_alert=True)
            await state.clear()
            await callback.message.edit_text(
                "Сталася помилка. Спробуйте /book ще раз.",
                reply_markup=main_menu_kb(),
            )
            return

        text = (
            "✔️ Ви записалися!\n\n"
            f"Послуга: {service.name}\n"
            f"Дата та час: {booking.start_datetime.strftime('%d.%m.%Y %H:%М')}\n"
            f"Тривалість: {booking.duration_minutes} хв\n"
        )
        if booking.price is not None:
            text += f"Ціна: {booking.price:.0f} грн\n"
        text += f"Спосіб оплати: {'Картка' if payment_method == 'card' else 'Готівка'}\n"
        text += f"Статус: {booking.status}\n"
        text += f"ID запису: {booking.id}\n"

        if payment_method == "card":
            number, holder = get_card_details(db)
            text += f"\nРеквізити для оплати карткою:\nНомер: {number}\nОтримувач: {holder}\n"

        await callback.message.edit_text(text)

        ics_content = generate_ics_content(
            booking=booking,
            service=service,
            user=user,
        )
        ics_bytes = ics_content.encode("utf-8")

        doc = BufferedInputFile(
            file=ics_bytes,
            filename=f"booking_{booking.id}.ics",
        )

        await callback.message.answer_document(
            document=doc,
            caption="Додайте цей файл у календар, щоб не забути про запис.",
        )

    await state.clear()

    await callback.message.answer(
        "Ви можете продовжити користуватись ботом. Меню внизу:",
        reply_markup=main_reply_kb(),
    )

    await callback.answer()
