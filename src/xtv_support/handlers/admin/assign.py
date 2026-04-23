from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup

from xtv_support.config.settings import settings
from xtv_support.core.constants import CallbackPrefix
from xtv_support.core.callback_data import CbAssignPick
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import audit as audit_repo
from xtv_support.infrastructure.db import projects as projects_repo
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.middlewares.admin_guard import require_admin
from xtv_support.services.tickets import topic_service
from xtv_support.ui.primitives.card import Card, edit_card, send_card
from xtv_support.ui.keyboards.base import btn, chunk
from xtv_support.ui.templates import user_messages
from xtv_support.utils.ids import safe_objectid, short_ticket_id

log = get_logger("admin.assign")


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_ASSIGN))
async def open_assign_picker(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    _, ticket_id = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id)
    if oid is None:
        await callback.answer("Invalid ticket.", show_alert=True)
        return
    buttons = []
    for admin_id in settings.ADMIN_IDS:
        try:
            admin = await client.get_users(admin_id)
            label = admin.first_name or f"Admin {admin_id}"
        except Exception:  # noqa: BLE001
            label = f"Admin {admin_id}"
        buttons.append(btn(label, f"{CallbackPrefix.TICKET_ASSIGN_PICK}|{ticket_id}|{admin_id}"))
    # Option to unassign
    buttons.append(btn("Unassign", f"{CallbackPrefix.TICKET_ASSIGN_PICK}|{ticket_id}|0"))
    keyboard = InlineKeyboardMarkup(chunk(buttons, per_row=2))
    try:
        await callback.message.reply_text(
            f"👨‍💻 <b>Assign ticket</b> #{short_ticket_id(oid)}\nPick an admin or unassign.",
            parse_mode="html",
            reply_markup=keyboard,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("assign.open_failed", error=str(exc))
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_ASSIGN_PICK))
async def pick_assignee(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    cb = CbAssignPick.unpack(callback.data)
    oid = safe_objectid(cb.ticket_id)
    if oid is None:
        await callback.answer("Invalid ticket.", show_alert=True)
        return

    new_assignee = cb.admin_id or None
    await tickets_repo.assign(
        ctx.db, oid, assignee_id=new_assignee, assigned_by=callback.from_user.id
    )
    await audit_repo.log(
        ctx.db,
        actor_id=callback.from_user.id,
        action="ticket.assign",
        target_type="ticket",
        target_id=str(oid),
        payload={"assignee": new_assignee},
    )

    ticket = await tickets_repo.get(ctx.db, oid)
    if not ticket:
        await callback.answer()
        return

    project = None
    if ticket.get("project_id"):
        project = await projects_repo.get(ctx.db, ticket["project_id"])

    user_name = str(ticket.get("user_id"))
    try:
        u = await client.get_users(ticket["user_id"])
        user_name = u.first_name or user_name
    except Exception:  # noqa: BLE001
        pass
    assignee_name = None
    if new_assignee:
        try:
            a = await client.get_users(new_assignee)
            assignee_name = a.first_name or f"Admin {new_assignee}"
        except Exception:  # noqa: BLE001
            assignee_name = f"Admin {new_assignee}"
    await topic_service.rerender_header(
        client,
        ctx.db,
        ticket=ticket,
        project=project,
        user_name=user_name,
        username=(await users_repo.get(ctx.db, ticket["user_id"]) or {}).get("username"),
        assignee_name=assignee_name,
    )

    if new_assignee:
        try:
            await send_card(
                client,
                new_assignee,
                user_messages.assignment_notification(
                    short_ticket_id(oid), project.get("name") if project else "Direct contact"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            log.info("assign.dm_failed", admin=new_assignee, error=str(exc))

    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await callback.answer("Saved.")

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
