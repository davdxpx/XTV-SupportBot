from __future__ import annotations

from pyrogram import Client
from pyrogram.types import Message

from app.constants import HandlerGroup
from app.core.context import get_context
from app.core.filters import is_private
from app.core.logger import get_logger
from app.db import users as users_repo

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
