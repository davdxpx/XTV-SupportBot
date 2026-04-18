from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.constants import HandlerGroup
from app.core.context import get_context
from app.core.filters import is_admin_forum_topic, is_admin_user
from app.core.logger import get_logger
from app.db import tickets as tickets_repo
from app.services import ticket_service

log = get_logger("topic.reply")


@Client.on_message(
    is_admin_forum_topic & is_admin_user & ~filters.service,
    group=HandlerGroup.TOPIC,
)
async def topic_admin_reply(client: Client, message: Message) -> None:
    """Any non-command admin message inside a ticket topic is forwarded to the user."""
    text = message.text or message.caption or ""
    if text.startswith("/"):
        return  # commands are handled in topic/commands.py

    ctx = get_context(client)
    topic_id = message.message_thread_id
    if not topic_id:
        return

    ticket = await tickets_repo.get_by_topic(ctx.db, topic_id)
    if not ticket:
        return
    if ticket.get("status") != "open":
        try:
            await message.reply_text("This ticket is closed.")
        except Exception:  # noqa: BLE001
            pass
        return

    try:
        await ticket_service.send_admin_reply_to_user(
            client, ctx.db, ticket=ticket, message=message
        )
        try:
            await message.reply_text("Delivered.")
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        log.warning("topic.deliver_failed", error=str(exc))
        try:
            await message.reply_text(f"Delivery failed: {exc}")
        except Exception:  # noqa: BLE001
            pass
