from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_admin_forum_topic, is_private
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.services.tickets import service as ticket_service
from xtv_support.ui.primitives.card import send_card
from xtv_support.ui.templates import user_messages

log = get_logger("user.close")


@Client.on_message(filters.command("close") & is_private, group=HandlerGroup.COMMAND)
async def user_close_cmd(client: Client, message: Message) -> None:
    ctx = get_context(client)
    user_id = message.from_user.id
    ticket = await tickets_repo.get_user_topic(ctx.db, user_id, None)
    if not ticket:
        # Check any open ticket even without topic.
        opens = await tickets_repo.list_by_user(ctx.db, user_id, limit=5)
        ticket = next((t for t in opens if t.get("status") == "open"), None)

    if not ticket:
        await send_card(client, user_id, user_messages.please_start_card())
        return

    await ticket_service.close_ticket(
        client,
        ctx.db,
        ticket=ticket,
        closed_by=user_id,
        reason="user_close",
        notify_user=True,
    )


@Client.on_message(filters.command("close") & is_admin_forum_topic, group=HandlerGroup.COMMAND)
async def admin_close_cmd(client: Client, message: Message) -> None:
    """Admin runs /close inside a ticket topic to close it."""
    ctx = get_context(client)
    topic_id = message.message_thread_id
    if not topic_id:
        return
    ticket = await tickets_repo.get_by_topic(ctx.db, topic_id)
    if not ticket:
        return
    if ticket.get("status") != "open":
        await message.reply_text("Ticket is already closed.")
        return
    await ticket_service.close_ticket(
        client,
        ctx.db,
        ticket=ticket,
        closed_by=message.from_user.id if message.from_user else None,
        reason="admin_close",
        notify_user=True,
    )
    try:
        await message.reply_text("Ticket closed.")
    except Exception:  # noqa: BLE001
        pass

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
