from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.constants import HandlerGroup
from app.core.context import get_context
from app.core.filters import is_admin_user, is_private
from app.db import tickets as tickets_repo
from app.ui.card import send_card
from app.ui.templates import user_messages


@Client.on_message(
    filters.command("history") & is_admin_user & is_private, group=HandlerGroup.COMMAND
)
async def admin_history(client: Client, message: Message) -> None:
    """Admin-only: /history <user_id> shows the last tickets for a user."""
    ctx = get_context(client)
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/history &lt;user_id&gt;</code>", parse_mode="html")
        return
    try:
        target_id = int(message.command[1])
    except ValueError:
        await message.reply_text("Invalid user id.")
        return
    tickets = await tickets_repo.list_by_user(ctx.db, target_id, limit=10)
    await send_card(client, message.chat.id, user_messages.history_card(target_id, tickets))

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
