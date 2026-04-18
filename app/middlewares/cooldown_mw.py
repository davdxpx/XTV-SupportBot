from __future__ import annotations

from pyrogram import Client
from pyrogram.types import Message

from app.constants import HandlerGroup
from app.core.context import get_context
from app.core.filters import is_admin_user, is_private, not_command
from app.core.logger import get_logger
from app.ui.card import send_card
from app.ui.templates.user_messages import cooldown_card

log = get_logger("cooldown_mw")


@Client.on_message(
    is_private & ~is_admin_user & not_command, group=HandlerGroup.MIDDLEWARE_GUARD
)
async def enforce_cooldown(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return

    decision = await ctx.cooldown.check(message.from_user.id)
    if decision.allowed:
        return

    try:
        await send_card(client, message.from_user.id, cooldown_card(decision.retry_after))
    except Exception as exc:  # noqa: BLE001 - best effort
        log.debug("cooldown.notify_failed", error=str(exc))

    message.stop_propagation()

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
