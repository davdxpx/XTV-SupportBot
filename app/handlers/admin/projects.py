from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery

from app.constants import CallbackPrefix, UserState
from app.core.context import get_context
from app.core.filters import cb_prefix
from app.db import projects as projects_repo
from app.db import tickets as tickets_repo
from app.db import users as users_repo
from app.middlewares.admin_guard import require_admin
from app.ui.card import edit_card, send_card
from app.ui.templates import admin_dashboard, project_wizard
from app.utils.ids import short_ticket_id


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECTS))
async def list_projects(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    projects = await projects_repo.list_all(ctx.db)
    await edit_card(
        client,
        callback.message.chat.id,
        callback.message.id,
        admin_dashboard.project_list(projects),
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECT_VIEW))
async def view_project(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, pid = callback.data.split("|", 1)
    project = await projects_repo.get(ctx.db, pid)
    if not project:
        await callback.answer("Not found.", show_alert=True)
        return
    await edit_card(
        client, callback.message.chat.id, callback.message.id, admin_dashboard.project_detail(project)
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECT_DELETE))
async def delete_project(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, pid = callback.data.split("|", 1)
    ok = await projects_repo.delete(ctx.db, pid)
    await callback.answer("Deleted." if ok else "Not found.", show_alert=True)
    projects = await projects_repo.list_all(ctx.db)
    await edit_card(
        client, callback.message.chat.id, callback.message.id, admin_dashboard.project_list(projects)
    )


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECT_TICKETS))
async def view_project_tickets(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, pid = callback.data.split("|", 1)
    tickets = await tickets_repo.list_open_by_project(ctx.db, pid)
    if not tickets:
        await callback.answer("No open tickets.", show_alert=True)
        return
    lines = [
        f"#{short_ticket_id(t['_id'])} • user <code>{t['user_id']}</code>" for t in tickets[:15]
    ]
    from app.ui.card import Card

    card = Card(
        title="Open tickets",
        body=lines,
        footer=f"Showing {min(len(tickets), 15)} of {len(tickets)}.",
    )
    await edit_card(client, callback.message.chat.id, callback.message.id, card)
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECT_CREATE))
async def start_wizard(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    await users_repo.set_state(ctx.db, callback.from_user.id, UserState.AWAITING_PROJECT_NAME)
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await send_card(client, callback.message.chat.id, project_wizard.ask_name())
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECT_TYPE))
async def project_type_pick(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, ptype = callback.data.split("|", 1)
    state = await users_repo.get(ctx.db, callback.from_user.id)
    if not state or state.get("state") != UserState.AWAITING_PROJECT_TYPE:
        await callback.answer("Session expired.", show_alert=True)
        return
    data = state.get("data", {}) or {}
    data["type"] = ptype
    if ptype == "support":
        await projects_repo.create(
            ctx.db,
            name=data["name"],
            description=data["desc"],
            created_by=callback.from_user.id,
            project_type="support",
        )
        await users_repo.clear_state(ctx.db, callback.from_user.id)
        await edit_card(
            client,
            callback.message.chat.id,
            callback.message.id,
            project_wizard.done_support(data["name"]),
        )
    else:
        await users_repo.set_state(
            ctx.db, callback.from_user.id, UserState.AWAITING_FEEDBACK_RATING, data
        )
        await edit_card(
            client,
            callback.message.chat.id,
            callback.message.id,
            project_wizard.ask_rating(),
        )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECT_RATING))
async def project_rating_pick(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, choice = callback.data.split("|", 1)
    state = await users_repo.get(ctx.db, callback.from_user.id)
    if not state or state.get("state") != UserState.AWAITING_FEEDBACK_RATING:
        await callback.answer("Session expired.", show_alert=True)
        return
    data = state.get("data", {}) or {}
    data["has_rating"] = choice == "yes"
    await users_repo.set_state(
        ctx.db, callback.from_user.id, UserState.AWAITING_FEEDBACK_TEXT, data
    )
    await edit_card(
        client, callback.message.chat.id, callback.message.id, project_wizard.ask_text()
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_PROJECT_TEXT))
async def project_text_pick(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, choice = callback.data.split("|", 1)
    state = await users_repo.get(ctx.db, callback.from_user.id)
    if not state or state.get("state") != UserState.AWAITING_FEEDBACK_TEXT:
        await callback.answer("Session expired.", show_alert=True)
        return
    data = state.get("data", {}) or {}
    data["has_text"] = choice == "yes"
    await users_repo.set_state(
        ctx.db, callback.from_user.id, UserState.AWAITING_FEEDBACK_TOPIC, data
    )
    await edit_card(
        client, callback.message.chat.id, callback.message.id, project_wizard.ask_topic_id()
    )
    await callback.answer()

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
