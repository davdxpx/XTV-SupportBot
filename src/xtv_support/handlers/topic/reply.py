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


async def _react(message: Message, emoji: str) -> None:
    """Best-effort emoji reaction on the admin's message. Silent if the
    client lacks reaction support in this pyrofork build."""
    try:
        # Pyrofork 2.x
        await message.react(emoji)
        return
    except TypeError:
        pass
    except AttributeError:
        pass
    except Exception as exc:  # noqa: BLE001
        log.debug("react.failed", error=str(exc))
        return

    # Some builds expose it on the client instead.
    try:
        await message._client.send_reaction(  # type: ignore[attr-defined]
            chat_id=message.chat.id, message_id=message.id, emoji=emoji
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("react.fallback_failed", error=str(exc))


@Client.on_message(
    is_admin_forum_topic & is_admin_user & ~filters.service,
    group=HandlerGroup.TOPIC,
)
async def topic_admin_reply(client: Client, message: Message) -> None:
    """Non-command admin messages in a ticket topic are forwarded to the user.

    Instead of replying with "Delivered." we react to the admin's own
    message with a ✅ on success or ❌ on failure, so the topic stays
    clean.
    """
    text = message.text or message.caption or ""
    if text.startswith("/"):
        return

    ctx = get_context(client)
    topic_id = message.message_thread_id
    if not topic_id:
        return

    ticket = await tickets_repo.get_by_topic(ctx.db, topic_id)
    if not ticket:
        return
    if ticket.get("status") != "open":
        await _react(message, "❌")
        return

    try:
        await ticket_service.send_admin_reply_to_user(
            client, ctx.db, ticket=ticket, message=message
        )
        await _react(message, "✅")
    except Exception as exc:  # noqa: BLE001
        log.warning("topic.deliver_failed", error=str(exc))
        await _react(message, "❌")


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
