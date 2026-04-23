from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.config.settings import settings
from xtv_support.core.constants import HandlerGroup
from xtv_support.core.logger import get_logger

log = get_logger("catchall")


@Client.on_message(filters.all, group=HandlerGroup.CATCH_ALL)
async def catchall(client: Client, message: Message) -> None:
    # In Pyrofork, every message propagates through all groups unless a
    # handler explicitly raises StopPropagation. That means this fires
    # even when lower-group handlers *did* take care of the message, so
    # we keep it at DEBUG to avoid noisy false-positive warnings.
    text = (message.text or message.caption or "")[:60]
    log.debug(
        "msg.catchall",
        chat_id=message.chat.id if message.chat else None,
        chat_type=str(message.chat.type) if message.chat else "?",
        user_id=message.from_user.id if message.from_user else None,
        thread_id=message.message_thread_id,
        text=text,
    )


async def report_error(client: Client, exc: BaseException, context: str = "") -> None:
    """Posts a structured error blockquote to ERROR_LOG_TOPIC_ID if configured."""
    log.exception("handler.error", context=context, error=str(exc))
    if not settings.ERROR_LOG_TOPIC_ID:
        return
    ctx_part = f" • {context}" if context else ""
    exc_name = type(exc).__name__
    body = (
        f"❌ <b>Internal error</b>{ctx_part}\n"
        f"<blockquote><code>{exc_name}: {exc}</code></blockquote>"
    )
    try:
        await client.send_message(
            settings.ADMIN_CHANNEL_ID,
            body,
            parse_mode="html",
            message_thread_id=settings.ERROR_LOG_TOPIC_ID,
        )
    except Exception as report_exc:  # noqa: BLE001
        log.warning("report_error.failed", error=str(report_exc))

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
