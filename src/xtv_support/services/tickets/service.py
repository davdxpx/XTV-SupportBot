from __future__ import annotations

from datetime import timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import RPCError
from pyrogram.types import Message

from xtv_support.config.settings import settings
from xtv_support.core.errors import TopicCreationError, TopicsNotSupported
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
    """Create a ticket from a Telegram message — thin adapter over :func:`create_ticket`."""
    user = message.from_user
    text, media_type, file_id = _extract_message(message)
    return await create_ticket(
        client,
        db,
        user_id=user.id,
        user_name=user.first_name or user.username or f"User {user.id}",
        username=user.username,
        project=project,
        text=text,
        media_type=media_type,
        file_id=file_id,
        contact_uuid=contact_uuid,
    )


async def create_ticket(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    user_id: int,
    user_name: str,
    username: str | None,
    project: dict[str, Any] | None,
    text: str,
    media_type: str = "text",
    file_id: str | None = None,
    contact_uuid: str | None = None,
) -> dict[str, Any]:
    """Create a ticket, attach a forum topic, post the header and confirm to the user.

    Path-agnostic core shared by the Telegram bot and the web/Mini-App API so
    both produce an identical ticket: a forum topic in the admin supergroup,
    the header card, the forwarded first message, and a user confirmation.

    Returns the fully hydrated ticket dict.
    """
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
            user_name=user_name,
            username=username,
            project=project,
        )
    except (TopicsNotSupported, TopicCreationError) as exc:
        # Fallback path: the topic couldn't be created (forum disabled, missing
        # permission, or ADMIN_CHANNEL_ID misconfigured). We still keep the
        # ticket and post everything to the channel root — the ticket stays
        # visible in the admin console regardless. topic_service already logged
        # the real cause at ERROR.
        fallback = True
        log.warning("ticket.topic_unavailable", ticket=str(ticket_id), error=str(exc))

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


async def attach_to_ticket(
    client: Client,
    db: AsyncIOMotorDatabase,
    *,
    ticket: dict[str, Any],
    data: bytes,
    filename: str,
    content_type: str | None,
    sender: str = "user",
    caption: str = "",
) -> tuple[str, str]:
    """Upload a file via the bot, post it into the ticket topic, record it.

    Storage IS Telegram: the bot sends the bytes into the admin supergroup
    (the ticket's topic, or the channel root in fallback) and we persist the
    returned ``file_id``. Returns ``(media_type, file_id)``.
    """
    import io

    bio = io.BytesIO(data)
    bio.name = filename or "attachment"
    is_image = bool(content_type and content_type.startswith("image/"))
    topic_id = ticket.get("topic_id")
    kwargs: dict[str, Any] = {"message_thread_id": topic_id} if topic_id else {}
    head = "<b>User</b>" if sender == "user" else "<b>Admin</b>"
    cap = f"{head}: {escape_html(caption)}" if caption else head

    if is_image:
        msg = await client.send_photo(
            settings.ADMIN_CHANNEL_ID, bio, caption=cap, parse_mode=ParseMode.HTML, **kwargs
        )
        media_type = "photo"
        file_id = msg.photo.file_id
    else:
        msg = await client.send_document(
            settings.ADMIN_CHANNEL_ID, bio, caption=cap, parse_mode=ParseMode.HTML, **kwargs
        )
        media_type = "document"
        file_id = msg.document.file_id

    await tickets_repo.append_history(
        db,
        ticket["_id"],
        sender=sender,
        text=caption or f"({media_type})",
        message_type=media_type,
        file_id=file_id,
    )
    return media_type, file_id


async def download_attachment(
    client: Client, ticket: dict[str, Any], index: int
) -> tuple[bytes, str] | None:
    """Fetch a stored attachment's bytes from Telegram. Returns (data, mime)."""
    history = ticket.get("history") or []
    if index < 0 or index >= len(history):
        return None
    entry = history[index]
    file_id = entry.get("file_id")
    if not file_id:
        return None
    bio = await client.download_media(file_id, in_memory=True)
    data = bio.getvalue() if hasattr(bio, "getvalue") else bytes(bio)
    mime = "image/jpeg" if entry.get("type") == "photo" else "application/octet-stream"
    return data, mime


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
