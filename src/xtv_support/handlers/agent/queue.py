"""Agent queue commands — ``/queue`` and ``/mytickets``.

``/queue`` lists open tickets routed to any team the caller belongs to
(via the ``tickets.team_id`` field written by the routing dispatcher).
``/mytickets`` narrows to tickets already assigned to the caller.

Both commands require the caller to have at least :attr:`Role.AGENT`.
"""
from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.errors import AdminOnly
from xtv_support.core.logger import get_logger
from xtv_support.core.rbac import require
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import teams as teams_repo

log = get_logger("queue_cmd")

MAX_ROWS = 20


async def _guard(message: Message) -> bool:
    try:
        require(Role.AGENT)
    except AdminOnly:
        await message.reply_text("🚫 Agent role required.")
        return False
    return True


def _ticket_line(doc: dict) -> str:
    tid = doc.get("_id") or "?"
    project = doc.get("project_id") or "—"
    priority = doc.get("priority") or "normal"
    tags = ",".join(doc.get("tags") or []) or "—"
    return (
        f"  • <code>#{tid}</code> · pri={priority} · "
        f"project={project} · tags={tags}"
    )


@Client.on_message(filters.private & filters.command("queue"), group=HandlerGroup.COMMAND)
async def queue_cmd(client: Client, message: Message) -> None:
    if not await _guard(message):
        return
    ctx = get_context(client)
    teams = await teams_repo.list_for_member(ctx.db, message.from_user.id)
    if not teams:
        await message.reply_text(
            "You are not a member of any team. Ask a supervisor to "
            "add you with <code>/team addmember</code>."
        )
        return

    team_ids = [t.id for t in teams]
    cursor = ctx.db.tickets.find(
        {
            "status": "open",
            "team_id": {"$in": team_ids},
        },
        projection={
            "_id": 1, "project_id": 1, "priority": 1, "tags": 1, "team_id": 1,
        },
    ).sort("created_at", -1).limit(MAX_ROWS)
    rows = [doc async for doc in cursor]
    if not rows:
        await message.reply_text(
            f"✅ Your queues (<b>{', '.join(team_ids)}</b>) are empty."
        )
        return

    lines = [f"<b>Queue — {len(rows)} open</b>"]
    for doc in rows:
        lines.append(f"  [{doc.get('team_id', '?')}] " + _ticket_line(doc).lstrip("  "))
    if len(rows) == MAX_ROWS:
        lines.append(f"<i>Showing the latest {MAX_ROWS}.</i>")
    await message.reply_text("\n".join(lines))


@Client.on_message(filters.private & filters.command("mytickets"), group=HandlerGroup.COMMAND)
async def mytickets_cmd(client: Client, message: Message) -> None:
    if not await _guard(message):
        return
    ctx = get_context(client)
    cursor = ctx.db.tickets.find(
        {
            "status": "open",
            "assignee_id": message.from_user.id,
        },
        projection={
            "_id": 1, "project_id": 1, "priority": 1, "tags": 1,
        },
    ).sort("created_at", -1).limit(MAX_ROWS)
    rows = [doc async for doc in cursor]
    if not rows:
        await message.reply_text("📭 You have no assigned open tickets.")
        return
    lines = [f"<b>Your tickets — {len(rows)} open</b>"]
    lines.extend(_ticket_line(doc) for doc in rows)
    if len(rows) == MAX_ROWS:
        lines.append(f"<i>Showing the latest {MAX_ROWS}.</i>")
    await message.reply_text("\n".join(lines))

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
