from __future__ import annotations

from pyrogram import Client
from pyrogram.types import CallbackQuery

from xtv_support.core.constants import CallbackPrefix, UserState
from xtv_support.core.context import get_context
from xtv_support.core.filters import cb_prefix
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.middlewares.admin_guard import require_admin
from xtv_support.ui.primitives.card import Card, edit_card


def _ask_anon_card() -> Card:
    from xtv_support.ui.keyboards.base import btn, rows

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


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
