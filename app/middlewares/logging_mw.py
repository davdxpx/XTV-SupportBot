from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.constants import HandlerGroup
from app.core.logger import get_logger

log = get_logger("msg")


@Client.on_message(filters.all, group=HandlerGroup.MIDDLEWARE_LOG)
async def log_incoming(_client: Client, message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id if message.chat else None
    log.debug(
        "msg.received",
        user_id=user_id,
        chat_id=chat_id,
        msg_id=message.id,
        thread_id=message.message_thread_id,
        text=(message.text or message.caption or "")[:60],
    )


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
