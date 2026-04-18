from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.constants import CallbackPrefix, HandlerGroup
from app.core.callback_data import CbPriorityPick
from app.core.context import get_context
from app.core.filters import cb_prefix, is_admin_forum_topic, is_admin_user
from app.core.logger import get_logger
from app.db import projects as projects_repo
from app.db import tags as tags_repo
from app.db import tickets as tickets_repo
from app.db import users as users_repo
from app.middlewares.admin_guard import require_admin
from app.services import topic_service
from app.utils.ids import safe_objectid

log = get_logger("topic.commands")


async def _rerender(client: Client, ctx, ticket: dict) -> None:
    project = None
    if ticket.get("project_id"):
        project = await projects_repo.get(ctx.db, ticket["project_id"])
    user_name = str(ticket["user_id"])
    try:
        u = await client.get_users(ticket["user_id"])
        user_name = u.first_name or user_name
    except Exception:  # noqa: BLE001
        pass
    assignee_name = None
    if ticket.get("assignee_id"):
        try:
            a = await client.get_users(ticket["assignee_id"])
            assignee_name = a.first_name or f"Admin {ticket['assignee_id']}"
        except Exception:  # noqa: BLE001
            assignee_name = f"Admin {ticket['assignee_id']}"
    await topic_service.rerender_header(
        client,
        ctx.db,
        ticket=ticket,
        project=project,
        user_name=user_name,
        username=(await users_repo.get(ctx.db, ticket["user_id"]) or {}).get("username"),
        assignee_name=assignee_name,
    )


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
        await message.reply_text("Usage: <code>/tag add|rm &lt;name&gt;</code>", parse_mode="html")
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
        await message.reply_text("Usage: <code>/assign &lt;admin_id&gt;</code> or <code>/assign me</code>", parse_mode="html")
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
    from app.ui.keyboards import btn, rows

    keyboard = rows(
        [
            btn("Low", f"{CallbackPrefix.TICKET_PRIORITY_PICK}|{ticket_id}|low"),
            btn("Normal", f"{CallbackPrefix.TICKET_PRIORITY_PICK}|{ticket_id}|normal"),
            btn("High", f"{CallbackPrefix.TICKET_PRIORITY_PICK}|{ticket_id}|high"),
        ],
    )
    try:
        await callback.message.reply_text(
            f"<blockquote>Priority for #{ticket_id[-6:]}.</blockquote>",
            parse_mode="html",
            reply_markup=keyboard,
        )
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
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await callback.answer("Saved.")


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_CLOSE))
async def close_button(client: Client, callback: CallbackQuery) -> None:
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
    from app.services import ticket_service

    await ticket_service.close_ticket(
        client,
        ctx.db,
        ticket=ticket,
        closed_by=callback.from_user.id,
        reason="header_button",
        notify_user=True,
    )
    await callback.answer("Closed.")

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
