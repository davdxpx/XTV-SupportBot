"""Agent inbox panel — saved views, ticket rows, bulk-action footer."""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.ui.primitives.panel import Panel, PanelButton, Tab

SAVED_VIEWS: tuple[tuple[str, str], ...] = (
    ("my_open", "My open"),
    ("unassigned", "Unassigned"),
    ("overdue", "Overdue"),
    ("high_priority", "High"),
    ("all_open", "All open"),
)

BULK_ACTIONS: tuple[tuple[str, str], ...] = (
    ("close", "✅ Close"),
    ("assign_me", "👤 Assign me"),
    ("priority_high", "🔥 Priority: High"),
    ("priority_low", "💤 Priority: Low"),
)


@dataclass(frozen=True, slots=True)
class InboxRow:
    ticket_id: str
    title: str
    priority: str = "normal"
    tags: tuple[str, ...] = ()
    unassigned: bool = False
    sla_at_risk: bool = False
    selected: bool = False


def _row_label(row: InboxRow) -> str:
    prio_icon = {"high": "🔥", "low": "💤"}.get(row.priority, "•")
    risk = " ⏰" if row.sla_at_risk else ""
    unassigned = " 🔓" if row.unassigned else ""
    box = "☑" if row.selected else "☐"
    truncated = row.title if len(row.title) <= 42 else row.title[:39] + "…"
    return f"{box} {prio_icon}{risk}{unassigned} {truncated}"


def render_inbox(
    *,
    active_view: str,
    rows: list[InboxRow],
    page: int = 1,
    total_pages: int = 1,
    selected_count: int = 0,
) -> Panel:
    tabs = tuple(
        Tab(key=key, label=label, callback=f"cb:v2:inbox:view:{key}", active=(key == active_view))
        for key, label in SAVED_VIEWS
    )

    action_rows: list[tuple[PanelButton, ...]] = []
    for row in rows:
        action_rows.append(
            (
                PanelButton(
                    label=_row_label(row),
                    callback=f"cb:v2:inbox:toggle:{row.ticket_id}",
                ),
            )
        )

    # Bulk actions footer only when something is selected.
    if selected_count > 0:
        action_rows.append(
            tuple(
                PanelButton(label=label, callback=f"cb:v2:inbox:bulk:{action}")
                for action, label in BULK_ACTIONS
            )
        )
        action_rows.append((PanelButton(label="Clear selection", callback="cb:v2:inbox:clear"),))

    body_lines = (
        f"<i>{selected_count} selected</i>" if selected_count > 0 else "",
        "" if rows else "<i>No tickets match this view.</i>",
    )

    prev_cb = f"cb:v2:inbox:page:{page - 1}" if page > 1 else None
    next_cb = f"cb:v2:inbox:page:{page + 1}" if page < total_pages else None

    return Panel(
        title="📋 Agent Inbox",
        subtitle=f"{sum(1 for _ in rows)} tickets",
        tabs=tabs,
        body=tuple(b for b in body_lines if b),
        action_rows=tuple(action_rows),
        page=page if total_pages > 1 else None,
        total_pages=total_pages,
        page_prev_cb=prev_cb,
        page_next_cb=next_cb,
    )


@dataclass(frozen=True, slots=True)
class CustomerHistorySummary:
    total_tickets: int = 0
    closed_tickets: int = 0
    csat_avg: float | None = None
    avg_first_response_min: float | None = None
    is_vip: bool = False
    is_blocked: bool = False


def render_customer_history(
    *,
    user_name: str,
    user_id: int,
    summary: CustomerHistorySummary,
    recent: list[tuple[str, str]] | None = None,
) -> str:
    lines: list[str] = [
        f"<b>👤 Customer history — {user_name}</b>",
        f"<i>ID {user_id}</i>",
        "",
    ]
    flags: list[str] = []
    if summary.is_vip:
        flags.append("💎 VIP")
    if summary.is_blocked:
        flags.append("🚫 Blocked")
    if flags:
        lines.append(" · ".join(flags))
        lines.append("")

    stats = [f"{summary.total_tickets} tickets total ({summary.closed_tickets} closed)"]
    if summary.csat_avg is not None:
        stats.append(f"⭐ {summary.csat_avg:.1f} CSAT avg")
    if summary.avg_first_response_min is not None:
        stats.append(f"⏱ {summary.avg_first_response_min:.0f}m first response")
    lines.append(" · ".join(stats))

    if recent:
        lines.append("")
        lines.append("<b>Last tickets</b>")
        for title, status in recent:
            truncated = title if len(title) <= 48 else title[:45] + "…"
            lines.append(f"• [{status}] {truncated}")

    return "\n".join(lines)
