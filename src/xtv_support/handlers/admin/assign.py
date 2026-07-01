from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery

from xtv_support.config.settings import settings
from xtv_support.core.callback_data import CbAssignPick
from xtv_support.core.constants import CallbackPrefix
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import audit as audit_repo
from xtv_support.infrastructure.db import projects as projects_repo
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.middlewares.admin_guard import require_admin
from xtv_support.services.tickets import topic_service
from xtv_support.ui.primitives.card import send_card
from xtv_support.ui.templates import user_messages
from xtv_support.ui.templates.ticket_header import assign_rows
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
    admins: list[tuple[str, int]] = []
    for admin_id in settings.ADMIN_IDS:
        try:
            admin = await client.get_users(admin_id)
            label = admin.first_name or f"Admin {admin_id}"
        except Exception:  # noqa: BLE001
            label = f"Admin {admin_id}"
        admins.append((label, admin_id))
    # Swap the header's own keyboard to the picker — everything stays in the
    # single header message (no throwaway messages).
    try:
        await callback.message.edit_reply_markup(reply_markup=assign_rows(ticket_id, admins))
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

    # Re-render the header in place — restores the default action row and shows
    # the new assignee. No extra messages.
    await topic_service.rerender_ticket_header(client, ctx.db, ticket=ticket)

    if new_assignee:
        project = None
        if ticket.get("project_id"):
            project = await projects_repo.get(ctx.db, ticket["project_id"])
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

    await callback.answer("Saved.")


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
