from __future__ import annotations

from pyrogram import Client
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_private
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import users as users_repo

log = get_logger("blocked_mw")


@Client.on_message(is_private, group=HandlerGroup.MIDDLEWARE_GUARD)
async def drop_blocked_users(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        ctx = get_context(client)
    except RuntimeError:
        return
    if await users_repo.is_blocked(ctx.db, message.from_user.id):
        log.info("blocked.drop", user_id=message.from_user.id)
        message.stop_propagation()


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
