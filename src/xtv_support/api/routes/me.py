"""``/api/v1/me`` — Telegram user-scoped endpoints.

Authenticated via the ``X-Telegram-Init-Data`` header (signed by the
bot token, validated in :mod:`xtv_support.api.auth_webapp`). This is
the entry point every end-user WebApp page calls first so the SPA can
hydrate with the user's ticket count, settings, and profile in a
single round-trip.

Phase 1 ships only the ``GET /me`` probe so Phase 2 / 3 pages have a
stable contract to build against. Ticket / settings routes join this
router in later phases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

_log = get_logger("api.me")


def build_router() -> APIRouter:
    from fastapi import APIRouter, Depends

    from xtv_support.api.auth_webapp import TelegramUser, current_tg_user
    from xtv_support.config.settings import settings

    router = APIRouter(prefix="/api/v1/me", tags=["me"])

    @router.get("")
    async def get_me(user: TelegramUser = Depends(current_tg_user)) -> dict:
        """Return the caller's Telegram profile + whether they're an admin.

        The admin flag lets the SPA decide up-front whether to render
        the user navigation (tickets, FAQ, settings) or the admin
        navigation (inbox, projects, rules, …) without a second call.
        """
        admin = user.id in set(settings.ADMIN_IDS)
        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "language_code": user.language_code,
            "is_admin": admin,
            "ui_mode": settings.ui_mode.value,
        }

    return router
