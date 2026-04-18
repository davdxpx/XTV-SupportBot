from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.config import settings
from app.constants import HandlerGroup
from app.core.logger import get_logger

log = get_logger("catchall")


@Client.on_message(filters.all, group=HandlerGroup.CATCH_ALL)
async def catchall(client: Client, message: Message) -> None:
    # Everything reaching this group has propagated through every other group
    # untouched, so we only emit a debug line for observability.
    log.debug(
        "msg.unhandled",
        chat_id=message.chat.id if message.chat else None,
        user_id=message.from_user.id if message.from_user else None,
        thread_id=message.message_thread_id,
    )


async def report_error(client: Client, exc: BaseException, context: str = "") -> None:
    """Posts a structured error blockquote to ERROR_LOG_TOPIC_ID if configured."""
    log.exception("handler.error", context=context, error=str(exc))
    if not settings.ERROR_LOG_TOPIC_ID:
        return
    ctx_part = f" \u2022 {context}" if context else ""
    exc_name = type(exc).__name__
    body = (
        f"<blockquote>Internal error{ctx_part}\n\n"
        f"<code>{exc_name}: {exc}</code></blockquote>"
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
