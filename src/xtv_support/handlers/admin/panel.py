"""Tabbed admin control panel — ``/panel``.

New entry point that doesn't touch the legacy ``/admin`` dashboard
(lives alongside in handlers/admin/dashboard.py). Admins can opt in to
the new UI by running ``/panel``; later releases will re-point ``/admin``
at it once UX is stable.
"""

from __future__ import annotations

from datetime import timedelta

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import CallbackQuery, Message

from xtv_support.core.constants import HandlerGroup
from xtv_support.core.context import get_context
from xtv_support.core.filters import is_admin_user, is_private
from xtv_support.core.logger import get_logger
from xtv_support.services.admin import presence
from xtv_support.ui.primitives.panel import Panel
from xtv_support.ui.templates.admin_panel import (
    OverviewStats,
    render_analytics_tab,
    render_broadcasts_tab,
    render_overview,
    render_projects_tab,
    render_rules_tab,
    render_settings_tab,
    render_teams_tab,
    render_tickets_tab,
)
from xtv_support.utils.time import utcnow

log = get_logger("admin.panel")


# ---------------------------------------------------------------------------
# Tab data collectors
# ---------------------------------------------------------------------------
async def _overview(ctx) -> OverviewStats:
    db = ctx.db
    open_tickets = await db.tickets.count_documents({"status": "open"})
    unassigned = await db.tickets.count_documents({"status": "open", "assignee_id": None})
    sla_at_risk = await db.tickets.count_documents({"status": "open", "sla_warned": True})
    try:
        active = await presence.count_active(db)
    except Exception:  # noqa: BLE001
        active = 0
    try:
        total_projects = await db.projects.count_documents({"active": True})
    except Exception:  # noqa: BLE001
        total_projects = 0
    try:
        total_users = await db.users.count_documents({})
    except Exception:  # noqa: BLE001
        total_users = 0
    return OverviewStats(
        open_tickets=open_tickets,
        sla_at_risk=sla_at_risk,
        unassigned=unassigned,
        active_agents=active,
        total_projects=total_projects,
        total_users=total_users,
    )


async def _tickets_stats(ctx) -> tuple[int, int]:
    today = utcnow() - timedelta(days=1)
    opened_today = await ctx.db.tickets.count_documents({"created_at": {"$gte": today}})
    closed_today = await ctx.db.tickets.count_documents(
        {"status": "closed", "closed_at": {"$gte": today}}
    )
    return opened_today, closed_today


async def _teams_stats(ctx) -> tuple[int, int]:
    num_teams = await ctx.db.teams.count_documents({})
    members = 0
    async for doc in ctx.db.teams.find({}, projection={"member_ids": 1}):
        members += len(doc.get("member_ids") or [])
    return num_teams, members


async def _projects_count(ctx) -> int:
    return await ctx.db.projects.count_documents({"active": True})


async def _rules_stats(ctx) -> tuple[int, int]:
    # Placeholder until Phase 4.6 lands — automation_rules collection
    # simply doesn't exist yet.
    try:
        total = await ctx.db.automation_rules.count_documents({})
        enabled = await ctx.db.automation_rules.count_documents({"enabled": True})
        return total, enabled
    except Exception:  # noqa: BLE001
        return 0, 0


async def _analytics(ctx, days: int = 7) -> tuple[int, int, float]:
    cursor = ctx.db.analytics_daily.find().sort("day", -1).limit(days)
    rollups = [d async for d in cursor]
    total = sum(int(d.get("total", 0)) for d in rollups)
    breached = sum(int(d.get("sla_breached", 0)) for d in rollups)
    sla_total = sum(int(d.get("sla_total", 0)) for d in rollups)
    ratio = 1.0 if sla_total == 0 else 1 - (breached / sla_total)
    return days, total, round(ratio, 3)


def _flags_snapshot(ctx) -> list[tuple[str, bool]]:
    flags = ctx.flags
    if flags is None:
        return []
    candidates = [
        "NEW_ONBOARDING",
        "CUSTOMER_HISTORY_PIN",
        "AGENT_INBOX",
        "AI_DRAFTS",
        "CSAT",
        "KB_GATE",
        "ANALYTICS_DIGEST",
    ]
    return [(name, bool(getattr(flags, name, False))) for name in candidates]


# ---------------------------------------------------------------------------
# Rendering + dispatch
# ---------------------------------------------------------------------------
async def _render_tab(ctx, tab: str) -> Panel:
    if tab == "overview":
        return render_overview(await _overview(ctx))
    if tab == "tickets":
        opened, closed = await _tickets_stats(ctx)
        return render_tickets_tab(opened, closed)
    if tab == "teams":
        num, members = await _teams_stats(ctx)
        return render_teams_tab(num, members)
    if tab == "projects":
        return render_projects_tab(await _projects_count(ctx))
    if tab == "rules":
        total, enabled = await _rules_stats(ctx)
        return render_rules_tab(total, enabled)
    if tab == "broadcasts":
        return render_broadcasts_tab()
    if tab == "analytics":
        days, total, ratio = await _analytics(ctx)
        return render_analytics_tab(days, total, ratio)
    if tab == "settings":
        return render_settings_tab(_flags_snapshot(ctx))
    return render_overview(await _overview(ctx))


async def _send_or_edit(
    client: Client,
    message: Message | None,
    cq: CallbackQuery | None,
    panel: Panel,
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


# ---------------------------------------------------------------------------
# Command + callback handlers
# ---------------------------------------------------------------------------
@Client.on_message(
    filters.command(["admin", "panel"]) & is_admin_user & is_private,
    group=HandlerGroup.COMMAND,
)
async def panel_cmd(client: Client, message: Message) -> None:
    ctx = get_context(client)
    if message.from_user:
        try:
            await presence.touch(ctx.db, message.from_user.id)
        except Exception:  # noqa: BLE001
            pass
    panel = await _render_tab(ctx, "overview")
    await _send_or_edit(client, message, None, panel)


@Client.on_callback_query(filters.regex(r"^cb:v2:admin:tab:"), group=HandlerGroup.COMMAND)
async def panel_tab_callback(client: Client, cq: CallbackQuery) -> None:
    ctx = get_context(client)
    if cq.from_user:
        try:
            await presence.touch(ctx.db, cq.from_user.id)
        except Exception:  # noqa: BLE001
            pass
    tab = (cq.data or "").split(":")[-1]
    panel = await _render_tab(ctx, tab)
    await _send_or_edit(client, None, cq, panel)


@Client.on_callback_query(filters.regex(r"^cb:v2:admin:flag:"), group=HandlerGroup.COMMAND)
async def panel_flag_toggle(client: Client, cq: CallbackQuery) -> None:
    """Persist a live feature-flag override.

    Flags live as env defaults; this collection overrides them per-deploy.
    The get_flags() cache will still return env defaults — a later phase
    plugs the override store into the flag accessor. For now the toggle
    is recorded and surfaced in the Settings tab so ops can audit intent
    before a re-deploy.
    """
    ctx = get_context(client)
    name = (cq.data or "").split(":")[-1]
    doc = await ctx.db.admin_overrides.find_one({"_id": "flags"}) or {"_id": "flags"}
    flips: dict = dict(doc.get("flags") or {})
    flips[name] = not bool(flips.get(name, getattr(ctx.flags, name, False)))
    await ctx.db.admin_overrides.update_one(
        {"_id": "flags"}, {"$set": {"flags": flips, "updated_at": utcnow()}}, upsert=True
    )
    await cq.answer(f"Flag {name} toggled (takes effect on next deploy).", show_alert=False)
    panel = await _render_tab(ctx, "settings")
    await _send_or_edit(client, None, cq, panel)


@Client.on_callback_query(
    filters.regex(r"^cb:v2:admin:(open_inbox|rotate_secrets|find_ticket)$"),
    group=HandlerGroup.COMMAND,
)
async def panel_shortcuts(client: Client, cq: CallbackQuery) -> None:
    action = (cq.data or "").split(":")[-1]
    tips = {
        "open_inbox": "Agent cockpit lands in Phase 4.5 — the button will jump there then. For now run /queue.",
        "rotate_secrets": "Run scripts/rotate_secrets.py in the container to rotate. UI wire-up pending.",
        "find_ticket": "Send the ticket ID as a message — /find <id> will work once the inbox is live.",
    }
    await cq.answer(tips.get(action, ""), show_alert=True)
