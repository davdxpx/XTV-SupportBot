from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from app.constants import CallbackPrefix, HandlerGroup
from app.core.context import get_context
from app.core.filters import cb_prefix, is_admin_user, is_private
from app.core.logger import get_logger
from app.db import projects as projects_repo
from app.db import users as users_repo
from app.middlewares.admin_guard import require_admin
from app.ui.card import edit_card, send_card
from app.ui.templates import admin_dashboard

log = get_logger("admin.dashboard")


async def _stats(db) -> tuple[int, int, int, int]:
    total_projects = len(await projects_repo.list_all(db))
    total_users = await users_repo.count(db)
    total_tickets = await db.tickets.count_documents({})
    open_tickets = await db.tickets.count_documents({"status": "open"})
    return total_projects, total_users, total_tickets, open_tickets


@Client.on_message(
    filters.command("admin") & is_admin_user & is_private, group=HandlerGroup.COMMAND
)
async def admin_entry(client: Client, message: Message) -> None:
    ctx = get_context(client)
    projects, users, tickets, open_t = await _stats(ctx.db)
    await send_card(
        client,
        message.chat.id,
        admin_dashboard.dashboard(
            projects=projects, users=users, tickets=tickets, open_tickets=open_t
        ),
    )


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_HOME))
async def back_home(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    projects, users, tickets, open_t = await _stats(ctx.db)
    await edit_card(
        client,
        callback.message.chat.id,
        callback.message.id,
        admin_dashboard.dashboard(
            projects=projects, users=users, tickets=tickets, open_tickets=open_t
        ),
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_CLOSE))
async def close_dashboard(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await callback.answer()
