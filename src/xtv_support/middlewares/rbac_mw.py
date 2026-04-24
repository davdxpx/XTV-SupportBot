"""RBAC middleware — pyrofork glue over :mod:`xtv_support.core.rbac`.

Resolves the caller's role on every private-chat update and sets
:data:`current_role` so downstream handlers can call
:func:`xtv_support.core.rbac.require` without threading the role
through their signatures.

All decision logic lives in :mod:`xtv_support.core.rbac`; this module
is intentionally thin so it can be unit-tested via the pure helpers
without a live pyrofork Client.
"""

from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.errors import AdminOnly
from xtv_support.core.filters import is_private
from xtv_support.core.logger import get_logger
from xtv_support.core.rbac import (  # re-exported for backwards compatibility
    current,
    current_role,
    decide,
    require,
    resolve_role,
)
from xtv_support.domain.enums import Role

log = get_logger("rbac_mw")

__all__ = [
    "current",
    "current_role",
    "decide",
    "require",
    "require_from_callback",
    "resolve_role",
]


async def require_from_callback(callback: CallbackQuery, *required: Role) -> None:
    """Answer the callback with a user-friendly error + raise :class:`AdminOnly`.

    Convenience wrapper for the most common call site — callback
    handlers that can't proceed without admin rights.
    """
    if decide(current(), required):
        return
    log.info(
        "rbac.denied_callback",
        actual=str(current()),
        required=[str(r) for r in required],
        data=callback.data,
    )
    try:
        await callback.answer("Insufficient permissions.", show_alert=True)
    except Exception:  # noqa: BLE001
        pass
    raise AdminOnly()


@Client.on_message(is_private, group=HandlerGroup.MIDDLEWARE_GUARD)
async def set_role_for_message(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    role = await resolve_role(
        ctx.db,
        message.from_user.id,
        legacy_admin_ids=ctx.settings.ADMIN_IDS,
    )
    current_role.set(role)


@Client.on_callback_query(group=HandlerGroup.MIDDLEWARE_GUARD)
async def set_role_for_callback(client: Client, callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    role = await resolve_role(
        ctx.db,
        callback.from_user.id,
        legacy_admin_ids=ctx.settings.ADMIN_IDS,
    )
    current_role.set(role)


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
