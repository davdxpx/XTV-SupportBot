"""Legacy admin guard — kept as a shim over the RBAC middleware.

Pre-Phase-5 handlers import :func:`require_admin` directly. We keep that
API stable by delegating to the RBAC permission helpers — admins
defined in ``settings.ADMIN_IDS`` still pass automatically, and users
promoted via the new ``roles`` collection also pass now.
"""
from __future__ import annotations

from pyrogram.types import CallbackQuery

from xtv_support.config.settings import settings
from xtv_support.core.errors import AdminOnly
from xtv_support.core.logger import get_logger
from xtv_support.domain.enums import Role
from xtv_support.core.rbac import current as current_role
from xtv_support.core.rbac import decide

log = get_logger("admin_guard")


async def require_admin(callback: CallbackQuery) -> None:
    """Raise :class:`AdminOnly` when the caller lacks admin rights.

    Two sources are checked, in order:
    1. The RBAC-resolved role on the active update (set by
       :mod:`xtv_support.middlewares.rbac_mw`). Any role at or above
       :attr:`Role.ADMIN` passes.
    2. ``settings.ADMIN_IDS`` — legacy safety net for deployments that
       might momentarily have an unresolved role (e.g. before the
       first migration run).
    """
    if decide(current_role(), (Role.ADMIN,)):
        return
    if callback.from_user and callback.from_user.id in settings.ADMIN_IDS:
        return

    log.info(
        "admin_guard.denied",
        user_id=callback.from_user.id if callback.from_user else None,
        data=callback.data,
        role=str(current_role()),
    )
    try:
        await callback.answer("Admin only.", show_alert=True)
    except Exception:  # noqa: BLE001
        pass
    raise AdminOnly()


def is_admin_id(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.ADMIN_IDS)

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
