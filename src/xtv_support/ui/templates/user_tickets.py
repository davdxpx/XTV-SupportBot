from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from xtv_support.core.constants import CallbackPrefix
from xtv_support.ui.keyboards.base import btn
from xtv_support.ui.primitives.card import Card
from xtv_support.utils.text import escape_html, truncate
from xtv_support.utils.time import humanize_delta, utcnow


def _has_new_reply(ticket: dict[str, Any], last_seen: datetime | None) -> bool:
    last_admin = ticket.get("last_admin_msg_at")
    if not last_admin:
        return False
    if last_seen is None:
        return True
    if last_admin.tzinfo is None:
        last_admin = last_admin.replace(tzinfo=UTC)
    return last_admin > last_seen


def _status_icon(ticket: dict[str, Any], has_new: bool) -> str:
    if ticket.get("status") == "closed":
        return "🔴"
    return "🔵" if has_new else "🟢"


def _type_icon(ticket: dict[str, Any]) -> str:
    if ticket.get("contact_uuid") and not ticket.get("project_id"):
        return "📞"
    return "🎫"


def list_card(
    tickets: list[dict[str, Any]],
    projects_by_id: dict[str, dict[str, Any]],
    *,
    last_seen: datetime | None,
    page: int = 0,
    per_page: int = 5,
) -> Card:
    total = len(tickets)
    new_count = sum(1 for t in tickets if _has_new_reply(t, last_seen))

    if total == 0:
        return Card(
            title="📜 Your tickets",
            body=[
                "You haven't opened any tickets yet.",
                "Use /start to begin.",
            ],
        )

    start = page * per_page
    end = start + per_page
    slice_ = tickets[start:end]

    body: list[str] = [
        f"<b>{total}</b> total" + (f" • <b>{new_count}</b> with new replies" if new_count else ""),
        "",
    ]
    rows: list[list[InlineKeyboardButton]] = []
    for t in slice_:
        tid = str(t["_id"])
        short = tid[-6:]
        proj = projects_by_id.get(str(t.get("project_id"))) if t.get("project_id") else None
        proj_name = escape_html(proj.get("name", "")) if proj else "Direct contact"
        status = t.get("status", "open")
        new = _has_new_reply(t, last_seen)
        last = t.get("last_admin_msg_at") or t.get("last_user_msg_at") or t.get("created_at")
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        rel = humanize_delta(utcnow() - last) + " ago" if last else "—"

        body.append(
            f"{_status_icon(t, new)} {_type_icon(t)} "
            f"<code>#{short}</code> • {proj_name} • {status} • {rel}"
            + ("  ✨ <b>new</b>" if new else "")
        )

        label = f"{_status_icon(t, new)} #{short} • {proj.get('name') if proj else 'Contact'}"
        if new:
            label = "✨ " + label
        rows.append([btn(label[:60], f"{CallbackPrefix.USER_TICKETS_VIEW}|{tid}")])

    # Pagination
    pager: list[InlineKeyboardButton] = []
    if start > 0:
        pager.append(btn("‹ Prev", f"{CallbackPrefix.USER_TICKETS_LIST}|{page - 1}"))
    if end < total:
        pager.append(btn("Next ›", f"{CallbackPrefix.USER_TICKETS_LIST}|{page + 1}"))
    if pager:
        rows.append(pager)

    footer = (
        f"<i>Showing {start + 1}–{min(end, total)} of {total}.</i>" if total > per_page else None
    )
    return Card(
        title="📜 Your tickets",
        body=body,
        footer=footer,
        buttons=InlineKeyboardMarkup(rows),
    )


def _format_history_entry(entry: dict[str, Any]) -> str:
    sender = entry.get("sender", "?")
    text = entry.get("text") or ""
    ts = entry.get("timestamp")
    when = ts.strftime("%m-%d %H:%M") if ts else ""
    icon = {"user": "👤", "admin": "💬", "system": "⚙"}.get(sender, "•")
    media_type = entry.get("type", "text")
    media_suffix = ""
    if media_type == "photo":
        media_suffix = "  <i>[photo]</i>"
    elif media_type == "document":
        media_suffix = "  <i>[document]</i>"
    body = truncate(escape_html(text or "(no text)"), 200)
    return f"{icon} <i>{when}</i>  {body}{media_suffix}"


def detail_card(
    ticket: dict[str, Any],
    project: dict[str, Any] | None,
    *,
    history_tail: Iterable[dict[str, Any]] | None = None,
) -> Card:
    tid = str(ticket["_id"])
    short = tid[-6:]
    status = ticket.get("status", "open")
    created = ticket.get("created_at")
    created_fmt = created.strftime("%Y-%m-%d %H:%M") if created else "?"

    proj_name = escape_html(project.get("name")) if project else "Direct contact"
    assignee = ticket.get("assignee_id")
    assignee_line = f"Admin <code>{assignee}</code>" if assignee else "<i>unassigned</i>"
    tags = ticket.get("tags") or []
    tags_line = " ".join(f"#{escape_html(t)}" for t in tags) if tags else "—"

    body: list[str] = [
        f"<b>Ticket:</b> <code>#{short}</code>",
        f"<b>Project:</b> {proj_name}",
        f"<b>Status:</b> {status}",
        f"<b>Created:</b> {created_fmt}",
        f"<b>Assignee:</b> {assignee_line}",
        f"<b>Tags:</b> {tags_line}",
    ]

    history = list(history_tail or ticket.get("history") or [])[-8:]
    if history:
        body.append("")
        body.append("<b>Recent messages</b>")
        body.extend(_format_history_entry(e) for e in history)

    rows: list[list[InlineKeyboardButton]] = []
    if status == "open":
        rows.append(
            [
                btn("🔒 Close ticket", f"{CallbackPrefix.USER_TICKETS_CLOSE}|{tid}"),
                btn("🔙 Back", f"{CallbackPrefix.USER_TICKETS_LIST}|0"),
            ]
        )
    else:
        rows.append([btn("🔙 Back", f"{CallbackPrefix.USER_TICKETS_LIST}|0")])

    return Card(
        title=f"{_type_icon(ticket)} Ticket #{short}",
        body=body,
        footer=("<i>Send a message here to add to this ticket.</i>" if status == "open" else None),
        buttons=InlineKeyboardMarkup(rows),
    )


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
