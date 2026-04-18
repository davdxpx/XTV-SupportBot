from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery

from app.config import settings
from app.core.errors import AdminOnly
from app.core.logger import get_logger

log = get_logger("admin_guard")


async def require_admin(callback: CallbackQuery) -> None:
    """Raise AdminOnly if the callback was not fired by a listed admin."""
    if not callback.from_user or callback.from_user.id not in settings.ADMIN_IDS:
        log.info(
            "admin_guard.denied",
            user_id=callback.from_user.id if callback.from_user else None,
            data=callback.data,
        )
        await callback.answer("Admin only.", show_alert=True)
        raise AdminOnly()


def is_admin_id(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.ADMIN_IDS)
