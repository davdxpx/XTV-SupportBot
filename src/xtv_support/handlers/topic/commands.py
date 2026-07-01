from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.callback_data import CbPriorityPick
from xtv_support.core.constants import CallbackPrefix, HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix, is_admin_forum_topic, is_admin_user
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import tags as tags_repo
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.middlewares.admin_guard import require_admin
from xtv_support.services.tickets import topic_service
from xtv_support.ui.templates.ticket_header import confirm_close_rows, priority_rows
from xtv_support.utils.ids import safe_objectid

log = get_logger("topic.commands")


async def _rerender(client: Client, ctx, ticket: dict) -> None:
    await topic_service.rerender_ticket_header(client, ctx.db, ticket=ticket)


@Client.on_message(
    filters.command("tag") & is_admin_user & is_admin_forum_topic, group=HandlerGroup.COMMAND
)
async def cmd_tag(client: Client, message: Message) -> None:
    ctx = get_context(client)
    topic_id = message.message_thread_id
    ticket = await tickets_repo.get_by_topic(ctx.db, topic_id) if topic_id else None
    if not ticket:
        return
    args = message.command[1:]
    if len(args) < 2 or args[0] not in ("add", "rm", "remove"):
        await message.reply_text(
            "Usage: <code>/tag add|rm &lt;name&gt;</code>", parse_mode=ParseMode.HTML
        )
        return
    op, tag = args[0], args[1].lower()
    if not tags_repo.valid_name(tag):
        await message.reply_text("Invalid tag name.")
        return
    current = set(ticket.get("tags") or [])
    if op == "add":
        if tag in current:
            return
        current.add(tag)
    else:
        current.discard(tag)
    await ctx.db.tickets.update_one({"_id": ticket["_id"]}, {"$set": {"tags": list(current)}})
    ticket["tags"] = list(current)
    await _rerender(client, ctx, ticket)
    try:
        await message.reply_text(f"Tags: {', '.join('#' + t for t in sorted(current)) or '(none)'}")
    except Exception:  # noqa: BLE001
        pass


@Client.on_message(
    filters.command("assign") & is_admin_user & is_admin_forum_topic, group=HandlerGroup.COMMAND
)
async def cmd_assign(client: Client, message: Message) -> None:
    ctx = get_context(client)
    topic_id = message.message_thread_id
    ticket = await tickets_repo.get_by_topic(ctx.db, topic_id) if topic_id else None
    if not ticket:
        return
    args = message.command[1:]
    if not args:
        await message.reply_text(
            "Usage: <code>/assign &lt;admin_id&gt;</code> or <code>/assign me</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    target = args[0]
    if target == "me":
        new_assignee = message.from_user.id
    elif target == "none":
        new_assignee = None
    else:
        try:
            new_assignee = int(target)
        except ValueError:
            await message.reply_text("Invalid admin id.")
            return
    await tickets_repo.assign(
        ctx.db, ticket["_id"], assignee_id=new_assignee, assigned_by=message.from_user.id
    )
    ticket["assignee_id"] = new_assignee
    await _rerender(client, ctx, ticket)
    try:
        await message.reply_text("Saved.")
    except Exception:  # noqa: BLE001
        pass


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_PRIORITY))
async def open_priority_picker(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    _, ticket_id = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id)
    if oid is None:
        await callback.answer("Invalid.", show_alert=True)
        return
    # Swap the header keyboard to the priority picker in place.
    try:
        await callback.message.edit_reply_markup(reply_markup=priority_rows(ticket_id))
    except Exception as exc:  # noqa: BLE001
        log.warning("priority.picker_failed", error=str(exc))
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_PRIORITY_PICK))
async def priority_pick(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    cb = CbPriorityPick.unpack(callback.data)
    oid = safe_objectid(cb.ticket_id)
    if oid is None:
        await callback.answer()
        return
    if cb.priority not in ("low", "normal", "high"):
        await callback.answer("Invalid priority.", show_alert=True)
        return
    await tickets_repo.set_priority(ctx.db, oid, cb.priority)
    ticket = await tickets_repo.get(ctx.db, oid)
    if ticket:
        await _rerender(client, ctx, ticket)
    await callback.answer("Saved.")


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_ACTIONS))
async def back_to_actions(client: Client, callback: CallbackQuery) -> None:
    """◀ Back / Done from any picker — re-render the header to its default state."""
    await require_admin(callback)
    ctx = get_context(client)
    _, ticket_id = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id)
    if oid is None:
        await callback.answer()
        return
    ticket = await tickets_repo.get(ctx.db, oid)
    if ticket:
        await _rerender(client, ctx, ticket)
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_CLOSE))
async def close_button(client: Client, callback: CallbackQuery) -> None:
    """First press: ask for confirmation inside the header message."""
    await require_admin(callback)
    ctx = get_context(client)
    _, ticket_id = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id)
    if oid is None:
        await callback.answer()
        return
    ticket = await tickets_repo.get(ctx.db, oid)
    if not ticket or ticket.get("status") != "open":
        await callback.answer("Already closed.", show_alert=True)
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=confirm_close_rows(ticket_id))
    except Exception as exc:  # noqa: BLE001
        log.warning("close.confirm_failed", error=str(exc))
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_CLOSE_CONFIRM))
async def close_confirm(client: Client, callback: CallbackQuery) -> None:
    """Second press: actually close the ticket + topic and re-render the header."""
    await require_admin(callback)
    ctx = get_context(client)
    _, ticket_id = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id)
    if oid is None:
        await callback.answer()
        return
    ticket = await tickets_repo.get(ctx.db, oid)
    if not ticket or ticket.get("status") != "open":
        await callback.answer("Already closed.", show_alert=True)
        return
    from xtv_support.services.tickets import service as ticket_service

    await ticket_service.close_ticket(
        client,
        ctx.db,
        ticket=ticket,
        closed_by=callback.from_user.id,
        reason="header_button",
        notify_user=True,
    )
    # Re-render to the closed state (no buttons) in the same message.
    fresh = await tickets_repo.get(ctx.db, oid)
    if fresh:
        await _rerender(client, ctx, fresh)
    await callback.answer("Closed.")


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
