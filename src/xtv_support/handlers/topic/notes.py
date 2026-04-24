"""``/note`` command — internal notes visible only to agents.

Runs only inside the forum supergroup where topic threads live. Notes
are appended via :mod:`xtv_support.infrastructure.db.notes_repo` and
reflected on the ticket header re-render.
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import notes_repo
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.services.actions import ActionContext

log = get_logger("topic.notes")


async def _find_ticket_by_topic(ctx, topic_id: int | None):
    if topic_id is None:
        return None
    return await tickets_repo.get_by_topic(ctx.db, topic_id)


@Client.on_message(filters.command("note"), group=HandlerGroup.COMMAND)
async def add_note_cmd(client: Client, message: Message) -> None:
    ctx = get_context(client)
    if ctx.settings and message.chat and message.chat.id != ctx.settings.ADMIN_CHANNEL_ID:
        return  # not inside the admin forum

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.reply("Usage: <code>/note &lt;text&gt;</code>")
        return

    note_text = parts[1].strip()
    topic_id = getattr(message, "message_thread_id", None) or (
        message.reply_to_message.message_thread_id if message.reply_to_message else None
    )
    ticket = await _find_ticket_by_topic(ctx, topic_id)
    if ticket is None:
        await message.reply("No ticket bound to this topic.")
        return

    if ctx.actions is not None:
        exec_ctx = ActionContext(
            db=ctx.db,
            bus=ctx.bus,
            client=client,
            actor_id=message.from_user.id if message.from_user else 0,
            origin="bot",
        )
        res = await ctx.actions.execute(
            exec_ctx,
            "add_internal_note",
            ticket_id=str(ticket.get("_id")),
            params={"text": note_text},
        )
        if not res.ok:
            await message.reply(f"❌ Note failed: {res.detail}")
            return
    else:  # fallback: direct repo call
        await notes_repo.append_note(
            ctx.db,
            ticket.get("_id"),
            author_id=message.from_user.id if message.from_user else 0,
            text=note_text,
        )

    total = await notes_repo.count_notes(ctx.db, ticket.get("_id"))
    await message.reply(
        f"📝 Internal note added ({total} total — hidden from the customer).",
        quote=True,
    )
