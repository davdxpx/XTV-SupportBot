from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from app.constants import CallbackPrefix, HandlerGroup
from app.core.context import get_context
from app.core.filters import cb_prefix, is_private
from app.core.logger import get_logger
from app.db import projects as projects_repo
from app.db import tickets as tickets_repo
from app.db import users as users_repo
from app.services import ticket_service
from app.ui.card import edit_card, send_card
from app.ui.templates import user_tickets as tpl
from app.utils.ids import safe_objectid

log = get_logger("user.tickets")


async def _render_list(client: Client, chat_id: int, user_id: int, *, page: int, edit_msg_id: int | None = None) -> None:
    ctx = get_context(client)
    tickets = await tickets_repo.list_by_user(ctx.db, user_id, limit=50)
    last_seen = await users_repo.get_tickets_seen_at(ctx.db, user_id)

    # Hydrate project names in one batch.
    project_ids = {str(t["project_id"]) for t in tickets if t.get("project_id")}
    projects_by_id: dict[str, dict] = {}
    for pid in project_ids:
        p = await projects_repo.get(ctx.db, pid)
        if p:
            projects_by_id[str(p["_id"])] = p

    card = tpl.list_card(tickets, projects_by_id, last_seen=last_seen, page=page)

    if edit_msg_id is not None:
        await edit_card(client, chat_id, edit_msg_id, card)
    else:
        await send_card(client, chat_id, card)

    # Mark "seen" AFTER rendering so the user sees the "new" badges once.
    await users_repo.mark_tickets_seen(ctx.db, user_id)


@Client.on_message(filters.command("tickets") & is_private, group=HandlerGroup.COMMAND)
async def cmd_tickets(client: Client, message: Message) -> None:
    await _render_list(
        client, message.chat.id, message.from_user.id, page=0, edit_msg_id=None
    )


@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_TICKETS_LIST))
async def on_list(client: Client, callback: CallbackQuery) -> None:
    try:
        _, raw_page = callback.data.split("|", 1)
        page = max(0, int(raw_page))
    except ValueError:
        page = 0
    await _render_list(
        client,
        callback.message.chat.id,
        callback.from_user.id,
        page=page,
        edit_msg_id=callback.message.id,
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_TICKETS_VIEW))
async def on_view(client: Client, callback: CallbackQuery) -> None:
    ctx = get_context(client)
    _, ticket_id_raw = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id_raw)
    if oid is None:
        await callback.answer("Invalid ticket.", show_alert=True)
        return
    ticket = await tickets_repo.get(ctx.db, oid)
    if not ticket or ticket["user_id"] != callback.from_user.id:
        await callback.answer("Ticket not found.", show_alert=True)
        return
    project = None
    if ticket.get("project_id"):
        project = await projects_repo.get(ctx.db, ticket["project_id"])
    card = tpl.detail_card(ticket, project)
    await edit_card(client, callback.message.chat.id, callback.message.id, card)
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.USER_TICKETS_CLOSE))
async def on_close(client: Client, callback: CallbackQuery) -> None:
    ctx = get_context(client)
    _, ticket_id_raw = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id_raw)
    if oid is None:
        await callback.answer("Invalid ticket.", show_alert=True)
        return
    ticket = await tickets_repo.get(ctx.db, oid)
    if not ticket or ticket["user_id"] != callback.from_user.id:
        await callback.answer("Ticket not found.", show_alert=True)
        return
    if ticket.get("status") != "open":
        await callback.answer("Already closed.", show_alert=True)
        return
    await ticket_service.close_ticket(
        client,
        ctx.db,
        ticket=ticket,
        closed_by=callback.from_user.id,
        reason="user_close_from_tickets",
        notify_user=False,
    )
    # Refresh the detail view so user sees the new status.
    ticket = await tickets_repo.get(ctx.db, oid)
    project = None
    if ticket and ticket.get("project_id"):
        project = await projects_repo.get(ctx.db, ticket["project_id"])
    if ticket:
        card = tpl.detail_card(ticket, project)
        await edit_card(client, callback.message.chat.id, callback.message.id, card)
    await callback.answer("Closed.", show_alert=False)


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
