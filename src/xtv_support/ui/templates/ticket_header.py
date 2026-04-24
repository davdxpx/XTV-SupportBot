from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pyrogram.types import InlineKeyboardMarkup

from xtv_support.core.constants import CallbackPrefix
from xtv_support.ui.keyboards.base import btn, rows
from xtv_support.ui.primitives.card import Card
from xtv_support.ui.primitives.progress import bar as progress_bar
from xtv_support.ui.primitives.progress import percentage as pct_str
from xtv_support.utils.text import escape_html, truncate, user_mention
from xtv_support.utils.time import format_iso, humanize_delta


def _priority_label(prio: str) -> str:
    return {
        "low": "🟢 Low",
        "normal": "⚪ Normal",
        "high": "🔴 High",
    }.get(prio, prio.title())


def _sla_progress(ticket: dict[str, Any]) -> tuple[float, str]:
    created = ticket.get("created_at")
    deadline = ticket.get("sla_deadline")
    now = datetime.now(UTC)

    if not deadline or not created:
        return 0.0, "not set"

    total = (deadline - created).total_seconds()
    if total <= 0:
        return 1.0, "deadline reached"

    elapsed = (now - created).total_seconds()
    ratio = max(0.0, min(1.0, elapsed / total))

    remaining = deadline - now
    if remaining.total_seconds() <= 0:
        return 1.0, "🔥 breached"
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
    is_contact = bool(ticket.get("contact_uuid")) and not project
    project_name = escape_html(project.get("name")) if project else "Direct contact"
    project_type = (
        "contact" if is_contact else (project.get("type", "support") if project else "support")
    )

    mention = user_mention(user_id, user_name or f"User {user_id}")
    username_s = f"@{escape_html(username)}" if username else "—"
    created_fmt = format_iso(ticket.get("created_at"))

    if ticket.get("assignee_id"):
        assignee_label = user_mention(
            ticket["assignee_id"], assignee_name or f"Admin {ticket['assignee_id']}"
        )
    else:
        assignee_label = "<i>unassigned</i>"

    tags_rendered = " ".join(f"#{escape_html(t)}" for t in tags) if tags else "—"

    sla_pct, sla_status = _sla_progress(ticket)

    body: list[str] = [
        f"👤 <b>User:</b> {mention}  •  <code>{user_id}</code>",
        f"   <i>handle:</i> {username_s}",
        f"📂 <b>Type:</b> {project_type}  •  {_priority_label(priority)}",
        f"🕒 <b>Status:</b> {status}  •  {created_fmt}",
        f"👨‍💻 <b>Assignee:</b> {assignee_label}",
        f"🏷 <b>Tags:</b> {tags_rendered}",
        f"⏱ <b>SLA:</b> {sla_status}  •  {pct_str(sla_pct)}  {progress_bar(sla_pct, width=10)}",
    ]

    original = truncate(escape_html(ticket.get("message", "")), 400) or "(no initial text)"

    if is_contact:
        title = f"📞 Contact #{short_id} • {project_name}"
    else:
        title = f"🎫 Ticket #{short_id} • {project_name}"

    card = Card(
        title=title,
        body=body,
        quote=original,
        quote_expandable=True,
        footer="<i>Buttons below: assign, tag, priority, close.</i>",
        buttons=_buttons(ticket_id, status),
    )
    return card


def _buttons(ticket_id: str, status: str) -> InlineKeyboardMarkup | None:
    if status != "open":
        return None
    assign = btn("👨‍💻 Assign", f"{CallbackPrefix.TICKET_ASSIGN}|{ticket_id}")
    tag = btn("🏷 Tag", f"{CallbackPrefix.TICKET_TAG}|{ticket_id}")
    priority = btn("⚡ Priority", f"{CallbackPrefix.TICKET_PRIORITY}|{ticket_id}")
    close = btn("🔒 Close", f"{CallbackPrefix.TICKET_CLOSE}|{ticket_id}")
    return rows([assign, tag], [priority, close])


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
