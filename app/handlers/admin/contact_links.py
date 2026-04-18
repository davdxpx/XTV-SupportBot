from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery

from app.constants import CallbackPrefix, UserState
from app.core.context import get_context
from app.core.filters import cb_prefix
from app.db import users as users_repo
from app.middlewares.admin_guard import require_admin
from app.ui.card import Card, edit_card


def _ask_anon_card() -> Card:
    from app.ui.keyboards import btn, rows

    buttons = rows(
        [
            btn("Anonymous", f"{CallbackPrefix.ADMIN_CONTACT_ANON}|yes"),
            btn("Show name", f"{CallbackPrefix.ADMIN_CONTACT_ANON}|no"),
        ],
    )
    return Card(
        title="New Contact Link",
        body=["Should this contact appear anonymously to users?"],
        buttons=buttons,
    )


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_CONTACT_START))
async def contact_link_start(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    await edit_card(client, callback.message.chat.id, callback.message.id, _ask_anon_card())
    await callback.answer()


@Client.on_callback_query(cb_prefix(CallbackPrefix.ADMIN_CONTACT_ANON))
async def contact_link_anon(client: Client, callback: CallbackQuery) -> None:
    await require_admin(callback)
    ctx = get_context(client)
    _, choice = callback.data.split("|", 1)
    await users_repo.set_state(
        ctx.db,
        callback.from_user.id,
        UserState.AWAITING_CONTACT_NAME,
        {"is_anonymous": choice == "yes"},
    )
    card = Card(
        title="New Contact Link",
        body=[
            "Enter a display name for this link.",
            "Example: <i>Support Agent</i> or <i>Max</i>.",
            "Send /cancel to abort.",
        ],
    )
    await edit_card(client, callback.message.chat.id, callback.message.id, card)
    await callback.answer()
