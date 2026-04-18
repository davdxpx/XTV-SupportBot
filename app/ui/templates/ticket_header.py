from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pyrogram.types import InlineKeyboardMarkup

from app.constants import CallbackPrefix
from app.ui.card import Card
from app.ui.glyphs import DIVIDER
from app.ui.keyboards import btn, rows
from app.ui.progress import bar as progress_bar
from app.ui.progress import percentage as pct_str
from app.utils.text import escape_html, truncate, user_mention
from app.utils.time import format_iso, humanize_delta


def _priority_label(prio: str) -> str:
    return {"low": "Low", "normal": "Normal", "high": "High"}.get(prio, prio.title())


def _sla_progress(ticket: dict[str, Any]) -> tuple[float, str]:
    """Return (progress_pct, status_text) for the SLA bar.

    0.0 = fresh ticket, 1.0 = deadline reached, >1.0 (capped) = breached.
    """
    created = ticket.get("created_at")
    deadline = ticket.get("sla_deadline")
    now = datetime.now(timezone.utc)

    if not deadline or not created:
        return 0.0, "not set"

    total = (deadline - created).total_seconds()
    if total <= 0:
        return 1.0, "deadline reached"

    elapsed = (now - created).total_seconds()
    ratio = max(0.0, min(1.0, elapsed / total))

    remaining = deadline - now
    if remaining.total_seconds() <= 0:
        return 1.0, "breached"
    return ratio, f"{humanize_delta(remaining)} left"


def render(
    ticket: dict[str, Any],
    *,
    project: dict[str, Any] | None,
    user_name: str,
    username: str | None,
    assignee_name: str | None,
) -> Card:
    ticket_id = str(ticket["_id"])
    short_id = ticket_id[-6:]
    user_id = ticket["user_id"]
    status = ticket.get("status", "open")
    priority = ticket.get("priority", "normal")
    tags = ticket.get("tags") or []
    project_name = escape_html(project.get("name")) if project else "Direct contact"
    project_type = project.get("type", "support") if project else "contact"

    mention = user_mention(user_id, user_name or f"User {user_id}")
    username_s = f"@{escape_html(username)}" if username else "\u2014"
    created_fmt = format_iso(ticket.get("created_at"))

    if ticket.get("assignee_id"):
        assignee_label = user_mention(
            ticket["assignee_id"], assignee_name or f"Admin {ticket['assignee_id']}"
        )
    else:
        assignee_label = "Unassigned"

    tags_rendered = " ".join(f"#{escape_html(t)}" for t in tags) if tags else "\u2014"

    sla_pct, sla_status = _sla_progress(ticket)

    body_lines: list[str] = [
        f"User: {mention} \u2022 <code>{user_id}</code>",
        f"Handle: {username_s}",
        f"Type: {project_type} \u2022 Priority: {_priority_label(priority)}",
        f"Status: {status} \u2022 Created: {created_fmt}",
        f"Assignee: {assignee_label}",
        f"Tags: {tags_rendered}",
        "",
        f"SLA: {sla_status}",
        f"Progress: {pct_str(sla_pct)}",
        progress_bar(sla_pct),
        "",
        DIVIDER,
        truncate(escape_html(ticket.get("message", "")), 400) or "(no initial text)",
    ]

    keyboard = _buttons(ticket_id, status)

    title = f"Ticket #{short_id} \u2022 {project_name}"
    return Card(title=title, body=body_lines, buttons=keyboard)


def _buttons(ticket_id: str, status: str) -> InlineKeyboardMarkup | None:
    if status != "open":
        return None
    assign = btn("Assign", f"{CallbackPrefix.TICKET_ASSIGN}|{ticket_id}")
    tag = btn("Tag", f"{CallbackPrefix.TICKET_TAG}|{ticket_id}")
    priority = btn("Priority", f"{CallbackPrefix.TICKET_PRIORITY}|{ticket_id}")
    close = btn("Close", f"{CallbackPrefix.TICKET_CLOSE}|{ticket_id}")
    return rows([assign, tag], [priority, close])
