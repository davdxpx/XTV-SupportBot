from __future__ import annotations

import inspect
import random
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client, raw
from pyrogram.enums import ParseMode
from pyrogram.errors import RPCError

from xtv_support.config.settings import settings
from xtv_support.core.errors import TopicCreationError, TopicsNotSupported
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.ui.primitives.card import edit_card, send_card
from xtv_support.ui.templates.ticket_header import render as render_header
from xtv_support.utils.ids import short_ticket_id
from xtv_support.utils.retry import async_retry

log = get_logger("topic")


# ---------------------------------------------------------------------------
# Peer helpers
# ---------------------------------------------------------------------------


async def _input_channel(client: Client, chat_id: int) -> raw.types.InputChannel:
    peer = await client.resolve_peer(chat_id)
    if not hasattr(peer, "channel_id") or not hasattr(peer, "access_hash"):
        raise TopicCreationError(
            f"chat_id {chat_id} is not a supergroup / channel "
            f"(resolved peer type: {type(peer).__name__})"
        )
    return raw.types.InputChannel(
        channel_id=peer.channel_id,
        access_hash=peer.access_hash,
    )


def _rnd_id(client: Client) -> int:
    rnd = getattr(client, "rnd_id", None)
    if callable(rnd):
        return rnd()
    return random.SystemRandom().randint(1, 2**62)


# ---------------------------------------------------------------------------
# Pyrofork schema adapter
# ---------------------------------------------------------------------------


def _find_raw_class(name: str) -> type | None:
    """Look up a raw TL function class across known namespaces.

    Pyrofork versions disagree on whether CreateForumTopic /
    EditForumTopic live in ``raw.functions.channels`` (current schema,
    per https://core.telegram.org/method/channels.createForumTopic) or
    the legacy ``raw.functions.messages`` namespace. We iterate both.
    """
    for ns in ("channels", "messages"):
        mod = getattr(raw.functions, ns, None)
        if mod is None:
            continue
        cls = getattr(mod, name, None)
        if cls is not None:
            return cls
    return None


def _class_params(cls: type) -> set[str]:
    try:
        return set(inspect.signature(cls.__init__).parameters)
    except (ValueError, TypeError):
        return set()


async def _peer_kwarg(client: Client, params: set[str]) -> tuple[str, Any]:
    """Pick the right peer kwarg name (``channel`` vs ``peer``) for this
    class and resolve the admin chat to the matching type."""
    if "channel" in params:
        return "channel", await _input_channel(client, settings.ADMIN_CHANNEL_ID)
    if "peer" in params:
        return "peer", await client.resolve_peer(settings.ADMIN_CHANNEL_ID)
    raise TopicCreationError(
        f"CreateForumTopic/EditForumTopic in this pyrofork build has no "
        f"channel or peer parameter (got: {sorted(params)})"
    )


# ---------------------------------------------------------------------------
# Raw API wrappers
# ---------------------------------------------------------------------------


@async_retry(attempts=settings.TOPIC_CREATE_RETRY, backoff=1.8, exceptions=(RPCError,))
async def _create_forum_topic(client: Client, title: str) -> int:
    """Create a forum topic in ADMIN_CHANNEL_ID via the raw API.

    Returns the topic's thread id (== id of the service message that
    created the topic). Implemented per
    https://core.telegram.org/method/channels.createForumTopic.
    """
    cls = _find_raw_class("CreateForumTopic")
    if cls is None:
        raise TopicCreationError("Pyrofork has no CreateForumTopic in channels or messages")

    params = _class_params(cls)
    peer_key, peer_value = await _peer_kwarg(client, params)

    kwargs: dict[str, Any] = {
        peer_key: peer_value,
        "title": title[:128],
        "random_id": _rnd_id(client),
    }

    log.debug(
        "topic.raw.create",
        cls=f"{cls.__module__}.{cls.__name__}",
        peer_key=peer_key,
    )
    result = await client.invoke(cls(**kwargs))

    for update in getattr(result, "updates", []) or []:
        msg = getattr(update, "message", None)
        if msg is not None and getattr(msg, "id", None):
            return int(msg.id)
    raise TopicCreationError("topic created but message id was not returned by server")


async def _edit_forum_topic_raw(
    client: Client, topic_id: int, *, closed: bool | None = None
) -> None:
    cls = _find_raw_class("EditForumTopic")
    if cls is None:
        raise TopicCreationError("Pyrofork has no EditForumTopic")

    params = _class_params(cls)
    peer_key, peer_value = await _peer_kwarg(client, params)

    kwargs: dict[str, Any] = {
        peer_key: peer_value,
        "topic_id": topic_id,
    }
    if closed is not None and "closed" in params:
        kwargs["closed"] = closed

    log.debug(
        "topic.raw.edit",
        cls=f"{cls.__module__}.{cls.__name__}",
        peer_key=peer_key,
        closed=closed,
    )
    await client.invoke(cls(**kwargs))


# ---------------------------------------------------------------------------
# High-level helpers used by the service layer
# ---------------------------------------------------------------------------


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

    On failure, marks the ticket as ``topic_fallback=True`` so subsequent
    messages go straight to the admin channel (no thread).
    """
    ticket = await tickets_repo.get(db, ticket_id)
    if not ticket:
        raise TopicCreationError("ticket_missing")

    short = short_ticket_id(ticket_id)
    title = f"#{short} • {title_prefix}"[:128]

    try:
        topic_id = await _create_forum_topic(client, title)
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
    except TopicCreationError:
        await tickets_repo.set_topic(db, ticket_id, topic_id=None, fallback=True)
        raise

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
        await _edit_forum_topic_raw(client, topic_id, closed=True)
    except (RPCError, TopicCreationError) as exc:
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
    """Send a message into the ticket topic, or fall back to the admin chat
    without a thread if the ticket never got a topic (topic_fallback=True)."""
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
