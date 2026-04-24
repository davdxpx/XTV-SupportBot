"""Legacy ``/admin`` dashboard — now a thin bridge.

The actual ``/admin`` command lives in
:mod:`xtv_support.handlers.admin.panel` (tabbed control panel). This
module only keeps the two legacy callback handlers that existing cards
still send:

- ``ADMIN_HOME``  → re-render the Overview tab of the new panel
- ``ADMIN_CLOSE`` → delete the current admin card

The old ``admin_dashboard`` text template is gone; any code that used
it is rewired to go through the new panel renderer.
"""

from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery

from xtv_support.core.constants import CallbackPrefix
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix
from xtv_support.core.logger import get_logger
from xtv_support.middlewares.admin_guard import require_admin

log = get_logger("admin.dashboard")


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_HOME))
async def back_home(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    # Import here to avoid a circular import (panel imports from here too
    # via the handler registry).
    from xtv_support.handlers.admin.panel import _render_tab, _send_or_edit

    ctx = get_context(client)
    panel = await _render_tab(ctx, "overview")
    await _send_or_edit(client, None, callback, panel)


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_CLOSE))
async def close_dashboard(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await callback.answer()


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
