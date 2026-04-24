from __future__ import annotations

from datetime import timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import RPCError
from pyrogram.types import Message

from xtv_support.config.settings import settings
from xtv_support.core.errors import TopicsNotSupported
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import audit as audit_repo
from xtv_support.infrastructure.db import projects as projects_repo
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.services.tickets import topic_service
from xtv_support.ui.primitives.card import send_card
from xtv_support.ui.templates import user_messages
from xtv_support.utils.ids import short_ticket_id
from xtv_support.utils.text import escape_html
from xtv_support.utils.time import utcnow

log = get_logger("ticket_service")


def _extract_message(message: Message) -> tuple[str, str, str | None]:
    """Return (text, media_type, file_id)."""
    if message.photo:
        return message.caption or "(photo)", "photo", message.photo.file_id
    if message.document:
        return (
            message.caption or f"(document: {message.document.file_name})",
            "document",
            message.document.file_id,
        )
    text = message.text or message.caption or "(empty)"
    return text, "text", None


async def create_ticket_from_message(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    message: Message,
    project: dict[str, Any] | None,
    contact_uuid: str | None = None,
) -> dict[str, Any]:
    """Create a ticket, attach a forum topic, post the header and confirm to the user.

    Returns the fully hydrated ticket dict.
    """
    user = message.from_user
    user_id = user.id

    text, media_type, file_id = _extract_message(message)

    deadline = utcnow() + timedelta(minutes=settings.SLA_WARN_MINUTES)
    ticket_id = await tickets_repo.create(
        db,
        project_id=str(project["_id"]) if project else None,
        user_id=user_id,
        message=text,
        message_type=media_type,
        file_id=file_id,
        contact_uuid=contact_uuid,
        sla_deadline=deadline,
    )
    if ticket_id is None:
        raise RuntimeError("ticket_create_failed")

    short = short_ticket_id(ticket_id)

    is_contact = bool(contact_uuid) and not project
    project_name = project.get("name") if project else "Direct contact"
    # Topic title: 📞 prefix when it's a contact link, 🎫 when it's a
    # classic support ticket. Makes the two flows visually distinct in
    # the admin forum sidebar.
    title_prefix = f"📞 {project_name}" if is_contact else project_name
    fallback = False
    try:
        topic_id, fallback = await topic_service.ensure_topic_for_ticket(
            client,
            db,
            ticket_id=ticket_id,
            title_prefix=title_prefix,
            user_name=user.first_name or user.username or f"User {user_id}",
            username=user.username,
            project=project,
        )
    except TopicsNotSupported:
        # Fallback path: the supergroup doesn't support forum topics, so
        # we post everything to the channel root instead. ``topic_id``
        # stays unset on the ticket document and the handler branches on
        # ``fallback`` below.
        fallback = True
        log.warning("ticket.topic_unavailable", ticket=str(ticket_id))

    # Forward the original user message into the topic (or fallback to channel).
    ticket = await tickets_repo.get(db, ticket_id)
    if ticket:
        caption = (
            f"<b>From user:</b> {escape_html(text)}" if media_type == "text" else escape_html(text)
        )
        await topic_service.send_to_topic_or_fallback(
            client,
            ticket=ticket,
            text=caption,
            file_id=file_id,
            media_type=media_type,
        )

    # Confirm to the user.
    is_feedback = bool(project and project.get("type") == "feedback")
    is_contact = bool(contact_uuid) and not project
    await send_card(
        client,
        user_id,
        user_messages.ticket_created(short, is_feedback=is_feedback, is_contact=is_contact),
    )

    await audit_repo.log(
        db,
        actor_id=user_id,
        action="ticket.create",
        target_type="ticket",
        target_id=str(ticket_id),
        payload={"project_id": str(project["_id"]) if project else None, "fallback": fallback},
    )
    return ticket or {"_id": ticket_id}


async def append_user_reply(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    ticket: dict[str, Any],
    message: Message,
) -> None:
    text, media_type, file_id = _extract_message(message)
    await tickets_repo.append_history(
        db,
        ticket["_id"],
        sender="user",
        text=text,
        message_type=media_type,
        file_id=file_id,
    )
    caption = f"<b>User:</b> {escape_html(text)}" if media_type == "text" else escape_html(text)
    await topic_service.send_to_topic_or_fallback(
        client,
        ticket=ticket,
        text=caption,
        file_id=file_id,
        media_type=media_type,
    )


async def send_admin_reply_to_user(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    ticket: dict[str, Any],
    message: Message,
) -> None:
    text, media_type, file_id = _extract_message(message)
    await tickets_repo.append_history(
        db, ticket["_id"], sender="admin", text=text, message_type=media_type, file_id=file_id
    )
    user_id = ticket["user_id"]

    # Minimal delivery: plain text / caption, no "Support reply" frame.
    # HTML-escape so user-typed angle brackets don't break parsing.
    body = escape_html(text)
    try:
        if media_type == "photo" and file_id:
            await client.send_photo(user_id, file_id, caption=body, parse_mode=ParseMode.HTML)
        elif media_type == "document" and file_id:
            await client.send_document(user_id, file_id, caption=body, parse_mode=ParseMode.HTML)
        else:
            await client.send_message(user_id, body, parse_mode=ParseMode.HTML)
    except RPCError as exc:
        log.warning("ticket.deliver_failed", ticket=str(ticket["_id"]), error=str(exc))
        raise


async def close_ticket(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    ticket: dict[str, Any],
    closed_by: int | None,
    reason: str | None = None,
    notify_user: bool = True,
) -> None:
    short = short_ticket_id(ticket["_id"])
    await tickets_repo.close(db, ticket["_id"], closed_by=closed_by, reason=reason)
    topic_id = ticket.get("topic_id")
    if topic_id:
        await topic_service.close_topic(client, topic_id)
    if notify_user:
        closed_by_user = closed_by == ticket["user_id"]
        try:
            await send_card(
                client,
                ticket["user_id"],
                user_messages.ticket_closed(short, closed_by_user=closed_by_user),
            )
        except RPCError:
            pass
    await audit_repo.log(
        db,
        actor_id=closed_by or 0,
        action="ticket.close",
        target_type="ticket",
        target_id=str(ticket["_id"]),
        payload={"reason": reason},
    )


async def hydrate_project(
    db: AsyncIOMotorDatabase, ticket: dict[str, Any]
) -> dict[str, Any] | None:
    if not ticket.get("project_id"):
        return None
    return await projects_repo.get(db, ticket["project_id"])


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
