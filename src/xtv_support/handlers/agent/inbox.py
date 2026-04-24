"""Agent cockpit — ``/inbox``.

Persistent saved-view inbox for agents. Selection state lives in the
user FSM so a user can open /inbox, select tickets, switch views, and
still see their selection. Bulk actions delegate to the ActionExecutor
from Phase 4.1 so the execution path matches the API and rules engine.

Feature-flagged (``FEATURE_AGENT_INBOX``): off by default, flip on
once the team has been briefed.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_private
from xtv_support.core.logger import get_logger
from xtv_support.services.actions import ActionContext
from xtv_support.ui.primitives.panel import Panel
from xtv_support.ui.templates.agent_inbox import InboxRow, render_inbox
from xtv_support.utils.time import utcnow

log = get_logger("agent.inbox")

PAGE_SIZE = 10
SELECTION_STATE = "agent_inbox_selection"


# ---------------------------------------------------------------------------
# Query builders per view
# ---------------------------------------------------------------------------
def _query_for_view(view: str, actor_id: int) -> dict:
    base: dict[str, Any] = {"status": "open"}
    if view == "my_open":
        base["assignee_id"] = actor_id
    elif view == "unassigned":
        base["assignee_id"] = None
    elif view == "overdue":
        base["$or"] = [
            {"sla_warned": True},
            {"sla_deadline": {"$ne": None, "$lte": utcnow()}},
        ]
    elif view == "high_priority":
        base["priority"] = "high"
    # "all_open" / default: just status=open
    return base


async def _load_rows(ctx, view: str, actor_id: int, *, page: int) -> tuple[list[InboxRow], int]:
    query = _query_for_view(view, actor_id)
    cursor = (
        ctx.db.tickets.find(query)
        .sort("created_at", -1)
        .skip(max(0, (page - 1) * PAGE_SIZE))
        .limit(PAGE_SIZE)
    )
    total = await ctx.db.tickets.count_documents(query)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    selection = await _load_selection(ctx, actor_id)
    rows: list[InboxRow] = []
    soon = utcnow() - timedelta(minutes=0)
    async for doc in cursor:
        tid = str(doc.get("_id"))
        message = str(doc.get("message") or "").replace("\n", " ").strip()
        title = message or f"Ticket #{tid[-6:]}"
        rows.append(
            InboxRow(
                ticket_id=tid,
                title=title,
                priority=str(doc.get("priority") or "normal"),
                tags=tuple(doc.get("tags") or ()),
                unassigned=doc.get("assignee_id") is None,
                sla_at_risk=bool(doc.get("sla_warned"))
                or (bool(doc.get("sla_deadline")) and doc.get("sla_deadline") <= soon),
                selected=tid in selection,
            )
        )
    return rows, total_pages


# ---------------------------------------------------------------------------
# Selection state — stored on the user FSM ``data`` bag
# ---------------------------------------------------------------------------
async def _load_selection(ctx, actor_id: int) -> set[str]:
    if ctx.state is None:
        return set()
    data = await ctx.state.data(actor_id)
    return set(data.get(SELECTION_STATE) or [])


async def _save_selection(ctx, actor_id: int, selection: set[str]) -> None:
    if ctx.state is None:
        return
    await ctx.state.merge_data(actor_id, {SELECTION_STATE: list(selection)})


async def _current_view(ctx, actor_id: int) -> str:
    if ctx.state is None:
        return "my_open"
    data = await ctx.state.data(actor_id)
    return str(data.get("agent_inbox_view") or "my_open")


async def _set_view(ctx, actor_id: int, view: str) -> None:
    if ctx.state is None:
        return
    await ctx.state.merge_data(actor_id, {"agent_inbox_view": view})


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
async def _render(ctx, actor_id: int, *, page: int = 1) -> Panel:
    view = await _current_view(ctx, actor_id)
    rows, total_pages = await _load_rows(ctx, view, actor_id, page=page)
    selection = await _load_selection(ctx, actor_id)
    return render_inbox(
        active_view=view,
        rows=rows,
        page=page,
        total_pages=total_pages,
        selected_count=len(selection),
    )


async def _send_or_edit(
    client: Client, message: Message | None, cq: CallbackQuery | None, panel: Panel
) -> None:
    text, kb = panel.render()
    if cq is not None and cq.message is not None:
        try:
            await cq.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
                disable_web_page_preview=True,
            )
        finally:
            await cq.answer()
        return
    if message is not None:
        await client.send_message(
            message.chat.id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )


def _enabled(ctx) -> bool:
    return bool(getattr(ctx.flags, "AGENT_INBOX", False))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("inbox") & is_private, group=HandlerGroup.COMMAND)
async def inbox_cmd(client: Client, message: Message) -> None:
    ctx = get_context(client)
    if not _enabled(ctx):
        await message.reply(
            "The agent inbox is gated on <code>FEATURE_AGENT_INBOX=true</code>. "
            "For now use /queue.",
            parse_mode=ParseMode.HTML,
        )
        return
    actor = message.from_user.id if message.from_user else 0
    panel = await _render(ctx, actor, page=1)
    await _send_or_edit(client, message, None, panel)


@Client.on_callback_query(filters.regex(r"^cb:v2:inbox:"), group=HandlerGroup.COMMAND)
async def inbox_callback(client: Client, cq: CallbackQuery) -> None:
    ctx = get_context(client)
    if not _enabled(ctx):
        await cq.answer("Agent inbox is disabled.", show_alert=False)
        return
    actor = cq.from_user.id if cq.from_user else 0
    parts = (cq.data or "").split(":")
    # cb:v2:inbox:<action>[:<arg>]
    action = parts[3] if len(parts) >= 4 else ""
    arg = parts[4] if len(parts) >= 5 else ""

    if action == "view":
        await _set_view(ctx, actor, arg or "my_open")
        panel = await _render(ctx, actor, page=1)
        await _send_or_edit(client, None, cq, panel)
        return

    if action == "toggle":
        sel = await _load_selection(ctx, actor)
        if arg in sel:
            sel.discard(arg)
        else:
            sel.add(arg)
        await _save_selection(ctx, actor, sel)
        panel = await _render(ctx, actor, page=1)
        await _send_or_edit(client, None, cq, panel)
        return

    if action == "clear":
        await _save_selection(ctx, actor, set())
        panel = await _render(ctx, actor, page=1)
        await _send_or_edit(client, None, cq, panel)
        return

    if action == "page":
        try:
            page = int(arg)
        except ValueError:
            page = 1
        panel = await _render(ctx, actor, page=page)
        await _send_or_edit(client, None, cq, panel)
        return

    if action == "bulk":
        await _run_bulk(client, cq, ctx, actor, arg)
        return

    await cq.answer()


async def _run_bulk(client: Client, cq: CallbackQuery, ctx, actor_id: int, action: str) -> None:
    sel = await _load_selection(ctx, actor_id)
    if not sel:
        await cq.answer("Select tickets first.", show_alert=False)
        return

    if ctx.actions is None:
        await cq.answer("Action executor unavailable.", show_alert=True)
        return

    params: dict[str, Any] = {}
    impl = action
    if action == "assign_me":
        impl, params = "assign", {"assignee_id": actor_id}
    elif action == "priority_high":
        impl, params = "set_priority", {"priority": "high"}
    elif action == "priority_low":
        impl, params = "set_priority", {"priority": "low"}
    elif action == "close":
        impl, params = "close", {"reason": "bulk"}

    ok = 0
    failed = 0
    exec_ctx = ActionContext(
        db=ctx.db, bus=ctx.bus, client=client, actor_id=actor_id, origin="bulk"
    )
    for tid in list(sel):
        res = await ctx.actions.execute(exec_ctx, impl, ticket_id=tid, params=params)
        if res.ok:
            ok += 1
        else:
            failed += 1

    await _save_selection(ctx, actor_id, set())
    await cq.answer(f"Bulk {impl}: {ok} ok, {failed} failed", show_alert=True)
    panel = await _render(ctx, actor_id, page=1)
    await _send_or_edit(client, None, cq, panel)
