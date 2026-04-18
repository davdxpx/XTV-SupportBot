from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import RPCError

from app.config import settings
from app.core.errors import TopicCreationError, TopicsNotSupported
from app.core.logger import get_logger
from app.db import tickets as tickets_repo
from app.ui.card import send_card, edit_card
from app.ui.templates.ticket_header import render as render_header
from app.utils.ids import short_ticket_id
from app.utils.retry import async_retry

log = get_logger("topic")


@async_retry(attempts=settings.TOPIC_CREATE_RETRY, backoff=1.8, exceptions=(RPCError,))
async def _create_forum_topic(client: Client, title: str) -> Any:
    return await client.create_forum_topic(settings.ADMIN_CHANNEL_ID, title)


async def ensure_topic_for_ticket(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    ticket_id: ObjectId,
    title_prefix: str,
    user_name: str,
    username: str | None,
    project: dict[str, Any] | None,
) -> tuple[int | None, bool]:
    """Create a forum topic and post the header. Returns (topic_id, fallback).

    On failure returns (None, True) and the caller should inform the user
    while still keeping the ticket open.
    """
    ticket = await tickets_repo.get(db, ticket_id)
    if not ticket:
        raise TopicCreationError("ticket_missing")

    short = short_ticket_id(ticket_id)
    title = f"#{short} • {title_prefix}"[:128]

    try:
        topic = await _create_forum_topic(client, title)
        topic_id = topic.id if hasattr(topic, "id") else topic.message_thread_id
        await tickets_repo.set_topic(db, ticket_id, topic_id=topic_id, fallback=False)
    except RPCError as exc:
        message = getattr(exc, "MESSAGE", str(exc)) or str(exc)
        log.warning("topic.create_failed", error=message)
        if "TOPICS_NOT_AVAILABLE" in message or "TOPICS_DISABLED" in message:
            await tickets_repo.set_topic(db, ticket_id, topic_id=None, fallback=True)
            raise TopicsNotSupported(message) from exc
        if "CHAT_ADMIN_REQUIRED" in message or "ChatAdminRequired" in message:
            await tickets_repo.set_topic(db, ticket_id, topic_id=None, fallback=True)
            raise TopicsNotSupported(message) from exc
        raise TopicCreationError(message) from exc

    ticket = await tickets_repo.get(db, ticket_id)
    card = render_header(
        ticket,
        project=project,
        user_name=user_name,
        username=username,
        assignee_name=None,
    )
    header_msg = await send_card(
        client,
        settings.ADMIN_CHANNEL_ID,
        card,
        thread_id=topic_id,
    )
    await tickets_repo.set_header_msg(db, ticket_id, header_msg.id)
    log.info("topic.created", ticket=str(ticket_id), topic_id=topic_id)
    return topic_id, False


async def close_topic(client: Client, topic_id: int) -> None:
    try:
        await client.close_forum_topic(settings.ADMIN_CHANNEL_ID, topic_id)
    except RPCError as exc:
        log.warning("topic.close_failed", topic_id=topic_id, error=str(exc))


async def rerender_header(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    ticket: dict[str, Any],
    project: dict[str, Any] | None,
    user_name: str,
    username: str | None,
    assignee_name: str | None,
) -> None:
    header_msg_id = ticket.get("header_msg_id")
    if not header_msg_id:
        return
    card = render_header(
        ticket,
        project=project,
        user_name=user_name,
        username=username,
        assignee_name=assignee_name,
    )
    try:
        await edit_card(client, settings.ADMIN_CHANNEL_ID, header_msg_id, card)
    except RPCError as exc:
        log.warning("topic.header_edit_failed", error=str(exc))


async def send_to_topic_or_fallback(
    client: Client,
    *,
    ticket: dict[str, Any],
    text: str,
    file_id: str | None = None,
    media_type: str = "text",
) -> None:
    """Send a message into the ticket topic, or fall back to a direct post in
    ADMIN_CHANNEL_ID if the ticket had no topic (topic_fallback=True)."""
    topic_id = ticket.get("topic_id")
    target_chat = settings.ADMIN_CHANNEL_ID
    kwargs = {"message_thread_id": topic_id} if topic_id else {}

    try:
        if media_type == "photo" and file_id:
            await client.send_photo(
                target_chat, file_id, caption=text, parse_mode=ParseMode.HTML, **kwargs
            )
        elif media_type == "document" and file_id:
            await client.send_document(
                target_chat, file_id, caption=text, parse_mode=ParseMode.HTML, **kwargs
            )
        else:
            await client.send_message(
                target_chat, text, parse_mode=ParseMode.HTML, **kwargs
            )
    except RPCError as exc:
        log.warning("topic.send_failed", ticket=str(ticket.get("_id")), error=str(exc))

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
