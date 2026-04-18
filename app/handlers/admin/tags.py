from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup

from app.constants import CallbackPrefix, UserState
from app.core.callback_data import CbTagToggle
from app.core.context import get_context
from app.core.filters import cb_prefix
from app.core.logger import get_logger
from app.db import audit as audit_repo
from app.db import projects as projects_repo
from app.db import tags as tags_repo
from app.db import tickets as tickets_repo
from app.db import users as users_repo
from app.middlewares.admin_guard import require_admin
from app.services import topic_service
from app.ui.card import Card, edit_card
from app.ui.keyboards import btn, chunk
from app.ui.templates import admin_dashboard
from app.utils.ids import safe_objectid

log = get_logger("admin.tags")


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_TAGS))
async def tags_menu(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    tags = await tags_repo.list_all(ctx.db)
    await edit_card(
        client, callback.message.chat.id, callback.message.id, admin_dashboard.tags_menu(tags)
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_TAG_NEW))
async def tag_new_prompt(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    await users_repo.set_state(ctx.db, callback.from_user.id, UserState.AWAITING_TAG_NAME)
    await edit_card(
        client,
        callback.message.chat.id,
        callback.message.id,
        Card(
            title="New tag",
            body=[
                "Send the tag name.",
                "Allowed: <code>[a-z0-9_-]{1,24}</code>",
                "/cancel to abort.",
            ],
        ),
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_TAG_DEL))
async def tag_delete(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, name = callback.data.split("|", 1)
    ok = await tags_repo.delete(ctx.db, name)
    await audit_repo.log(ctx.db, actor_id=callback.from_user.id, action="tag.delete", target_id=name)
    tags = await tags_repo.list_all(ctx.db)
    await edit_card(
        client, callback.message.chat.id, callback.message.id, admin_dashboard.tags_menu(tags)
    )
    await callback.answer("Deleted." if ok else "Not found.")


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_TAG))
async def open_tag_picker(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, ticket_id = callback.data.split("|", 1)
    oid = safe_objectid(ticket_id)
    if oid is None:
        await callback.answer("Invalid.", show_alert=True)
        return
    ticket = await tickets_repo.get(ctx.db, oid)
    if not ticket:
        await callback.answer("Not found.", show_alert=True)
        return
    tags = await tags_repo.list_all(ctx.db)
    if not tags:
        await callback.answer("Create tags first via /admin \u203a Tags.", show_alert=True)
        return
    current = set(ticket.get("tags") or [])
    buttons = [
        btn(
            f"{'\u2713 ' if t['name'] in current else ''}#{t['name']}",
            f"{CallbackPrefix.TICKET_TAG_TOGGLE}|{ticket_id}|{t['name']}",
        )
        for t in tags
    ]
    keyboard = InlineKeyboardMarkup(chunk(buttons, per_row=2))
    try:
        await callback.message.reply_text(
            f"<blockquote>Toggle tags for #{ticket_id[-6:]}.</blockquote>",
            parse_mode="html",
            reply_markup=keyboard,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("tag.picker_failed", error=str(exc))
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.TICKET_TAG_TOGGLE))
async def tag_toggle(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    cb = CbTagToggle.unpack(callback.data)
    oid = safe_objectid(cb.ticket_id)
    if oid is None:
        await callback.answer()
        return
    await tickets_repo.toggle_tag(ctx.db, oid, cb.tag)
    await audit_repo.log(
        ctx.db,
        actor_id=callback.from_user.id,
        action="ticket.tag_toggle",
        target_type="ticket",
        target_id=str(oid),
        payload={"tag": cb.tag},
    )
    ticket = await tickets_repo.get(ctx.db, oid)
    project = None
    if ticket and ticket.get("project_id"):
        project = await projects_repo.get(ctx.db, ticket["project_id"])
    if ticket:
        user_name = str(ticket.get("user_id"))
        try:
            u = await client.get_users(ticket["user_id"])
            user_name = u.first_name or user_name
        except Exception:  # noqa: BLE001
            pass
        await topic_service.rerender_header(
            client,
            ctx.db,
            ticket=ticket,
            project=project,
            user_name=user_name,
            username=(await users_repo.get(ctx.db, ticket["user_id"]) or {}).get("username"),
            assignee_name=None,
        )
    await callback.answer("Updated.")
