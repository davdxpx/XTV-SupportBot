"""Drill-down admin control panel — ``/admin`` (alias: ``/panel``).

The admin UX is now **drill-down**, not tabbed. ``/admin`` opens a
landing card with a 2×4 grid of big category tiles. Tapping a tile
replaces the card with that section's dedicated view (its own
buttons, its own back button). The legacy ``cb:v2:admin:tab:*``
callbacks stay registered so existing keyboards (e.g. the teams menu's
"◀ Back" button) still land where expected.
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
    render_analytics_section,
    render_broadcasts_section,
    render_home,
    render_overview_section,
    render_projects_section,
    render_rules_section,
    render_settings_section,
    render_teams_section,
    render_tickets_section,
)
from xtv_support.utils.time import utcnow

log = get_logger("admin.panel")


# ---------------------------------------------------------------------------
# Data collectors (unchanged from the tabbed version)
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
        "CUSTOMER_HISTORY_PIN",
        "AGENT_INBOX",
        "AI_DRAFTS",
        "CSAT",
        "KB_GATE",
        "ANALYTICS_DIGEST",
    ]
    return [(name, bool(getattr(flags, name, False))) for name in candidates]


# ---------------------------------------------------------------------------
# Section router
# ---------------------------------------------------------------------------
async def _render_section(ctx, section: str) -> Panel:
    """Dispatch ``cb:v2:admin:section:<key>`` to the right renderer."""
    if section == "home":
        return render_home(await _overview(ctx))
    if section == "overview":
        return render_overview_section(await _overview(ctx))
    if section == "tickets":
        opened, closed = await _tickets_stats(ctx)
        return render_tickets_section(opened, closed)
    if section == "teams":
        num, members = await _teams_stats(ctx)
        return render_teams_section(num, members)
    if section == "projects":
        return render_projects_section(await _projects_count(ctx))
    if section == "rules":
        total, enabled = await _rules_stats(ctx)
        return render_rules_section(total, enabled)
    if section == "broadcasts":
        return render_broadcasts_section()
    if section == "analytics":
        days, total, ratio = await _analytics(ctx)
        return render_analytics_section(days, total, ratio)
    if section == "settings":
        return render_settings_section(_flags_snapshot(ctx))
    # Unknown key → fall back to home.
    return render_home(await _overview(ctx))


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
# Commands
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
    panel = await _render_section(ctx, "home")
    await _send_or_edit(client, message, None, panel)


# ---------------------------------------------------------------------------
# Callbacks — new ``cb:v2:admin:section:<key>`` + legacy ``:tab:<key>``
# ---------------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^cb:v2:admin:(section|tab):"), group=HandlerGroup.COMMAND)
async def panel_section_callback(client: Client, cq: CallbackQuery) -> None:
    """Route both the new ``section:*`` and legacy ``tab:*`` callbacks.

    Keeping the ``tab:`` alias means keyboards produced by older code
    paths (e.g. the teams menu's "◀ Back" button) still work — they
    just land on the section page instead of a tabbed view.
    """
    ctx = get_context(client)
    if cq.from_user:
        try:
            await presence.touch(ctx.db, cq.from_user.id)
        except Exception:  # noqa: BLE001
            pass
    section = (cq.data or "").split(":")[-1]
    panel = await _render_section(ctx, section)
    await _send_or_edit(client, None, cq, panel)


@Client.on_callback_query(filters.regex(r"^cb:v2:admin:flag:"), group=HandlerGroup.COMMAND)
async def panel_flag_toggle(client: Client, cq: CallbackQuery) -> None:
    """Persist a live feature-flag override and re-render the settings section."""
    ctx = get_context(client)
    name = (cq.data or "").split(":")[-1]
    doc = await ctx.db.admin_overrides.find_one({"_id": "flags"}) or {"_id": "flags"}
    flips: dict = dict(doc.get("flags") or {})
    flips[name] = not bool(flips.get(name, getattr(ctx.flags, name, False)))
    await ctx.db.admin_overrides.update_one(
        {"_id": "flags"},
        {"$set": {"flags": flips, "updated_at": utcnow()}},
        upsert=True,
    )
    await cq.answer(f"Flag {name} toggled (takes effect on next deploy).", show_alert=False)
    panel = await _render_section(ctx, "settings")
    await _send_or_edit(client, None, cq, panel)


@Client.on_callback_query(
    filters.regex(r"^cb:v2:admin:(open_inbox|rotate_secrets|find_ticket)$"),
    group=HandlerGroup.COMMAND,
)
async def panel_shortcuts(client: Client, cq: CallbackQuery) -> None:
    action = (cq.data or "").split(":")[-1]
    tips = {
        "open_inbox": "Agent cockpit: run /inbox (gated on FEATURE_AGENT_INBOX).",
        "rotate_secrets": (
            "Run scripts/rotate_secrets.py in the container to rotate. UI wire-up pending."
        ),
        "find_ticket": "Send the ticket ID as a message — /find <id> will work once the inbox is live.",
    }
    await cq.answer(tips.get(action, ""), show_alert=True)
