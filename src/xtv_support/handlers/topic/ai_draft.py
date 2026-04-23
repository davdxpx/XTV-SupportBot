"""/draft command inside a ticket topic.

Pulls the full conversation from the ticket, asks :func:`draft_reply`
for a suggestion, and posts the result back into the topic as an
expandable blockquote so the agent can copy-paste/edit before sending
to the user.

Requires ``FEATURE_AI_DRAFTS`` and Agent+ role.
"""
from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.errors import AdminOnly
from xtv_support.core.filters import is_admin_forum_topic
from xtv_support.core.logger import get_logger
from xtv_support.core.rbac import require
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.services.ai.drafts import draft_reply

log = get_logger("draft_cmd")


async def _ticket_for_topic(ctx, topic_id: int | None) -> dict | None:
    if topic_id is None:
        return None
    return await ctx.db.tickets.find_one({"topic_id": topic_id})


@Client.on_message(is_admin_forum_topic & filters.command("draft"), group=HandlerGroup.TOPIC)
async def draft_cmd(client: Client, message: Message) -> None:
    if not message.from_user:
        return
    try:
        require(Role.AGENT)
    except AdminOnly:
        await message.reply_text("🚫 Agent role required.")
        return

    ctx = get_context(client)
    flags = getattr(ctx, "flags", None)
    if not flags or not flags.is_enabled("AI_DRAFTS"):
        await message.reply_text(
            "AI reply-draft is disabled. Set <code>FEATURE_AI_DRAFTS=true</code>."
        )
        return

    container = getattr(ctx, "container", None)
    ai_client: AIClient | None = None
    if container is not None:
        try:
            ai_client = container.try_resolve(AIClient)
        except Exception:  # noqa: BLE001
            ai_client = None
    if ai_client is None or not ai_client.enabled:
        await message.reply_text(
            "AI layer is not configured. Check <code>AI_ENABLED</code> and provider keys."
        )
        return

    ticket = await _ticket_for_topic(ctx, message.message_thread_id)
    if not ticket:
        await message.reply_text("Can't find a ticket for this topic.")
        return

    conversation = _build_history(ticket)
    pending = ticket.get("message") or ""
    for entry in reversed(ticket.get("history") or []):
        if entry.get("sender") == "user" and entry.get("text"):
            pending = entry["text"]
            break

    busy = await message.reply_text("🧠 Drafting a reply…")
    result = await draft_reply(
        ai_client,
        conversation=conversation,
        pending_user_message=pending,
        user_id=ticket.get("user_id"),
        ticket_id=str(ticket.get("_id")),
    )
    if not result.ok:
        await busy.edit_text(f"❌ Draft failed: <code>{result.error}</code>")
        return

    await busy.edit_text(
        "<b>💡 Draft reply</b>\n\n"
        f"<blockquote expandable>{result.text}</blockquote>\n\n"
        f"<i>tokens={result.prompt_tokens + result.completion_tokens} · "
        f"cost=${result.cost_usd:.4f}</i>"
    )


def _build_history(ticket: dict) -> list[dict[str, str]]:
    """Flatten ``ticket.history`` into a chat-completions message list."""
    out: list[dict[str, str]] = []
    for entry in ticket.get("history") or []:
        sender = entry.get("sender") or "user"
        text = entry.get("text") or ""
        if not text:
            continue
        role = "user" if sender == "user" else "assistant"
        out.append({"role": role, "content": text})
    return out

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
