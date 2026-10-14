from __future__ import annotations

from aiogram import Router

from .services import router as services_router
from .booking import router as booking_router
from .my_bookings import router as my_bookings_router


def setup_client_routers() -> Router:
    router = Router()
    router.include_router(services_router)
    router.include_router(booking_router)
    router.include_router(my_bookings_router)
    return router
