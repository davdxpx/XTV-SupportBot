from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery

from app.constants import CallbackPrefix, UserState
from app.core.context import get_context
from app.core.filters import cb_prefix
from app.db import users as users_repo
from app.middlewares.admin_guard import require_admin
from app.ui.card import Card, edit_card
from app.ui.templates import admin_dashboard


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_USERS))
async def users_menu(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    await edit_card(
        client, callback.message.chat.id, callback.message.id, admin_dashboard.user_menu()
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_USERS_BLOCK))
async def block_prompt(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    await users_repo.set_state(ctx.db, callback.from_user.id, UserState.AWAITING_BLOCK_ID)
    await edit_card(
        client,
        callback.message.chat.id,
        callback.message.id,
        Card(title="Block user", body=["Send the numeric user id to block.", "/cancel to abort."]),
    )
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_USERS_UNBLOCK))
async def unblock_prompt(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    await users_repo.set_state(ctx.db, callback.from_user.id, UserState.AWAITING_UNBLOCK_ID)
    await edit_card(
        client,
        callback.message.chat.id,
        callback.message.id,
        Card(title="Unblock user", body=["Send the numeric user id to unblock.", "/cancel to abort."]),
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
