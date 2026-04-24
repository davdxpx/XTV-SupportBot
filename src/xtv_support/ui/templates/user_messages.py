from __future__ import annotations

from collections.abc import Sequence

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from xtv_support.core.constants import CallbackPrefix
from xtv_support.ui.keyboards.base import btn, chunk
from xtv_support.ui.primitives.card import Card
from xtv_support.utils.text import escape_html


def welcome_no_projects() -> Card:
    return Card(
        title="👋 Welcome",
        body=[
            "There are no active projects right now.",
            "Please check back later.",
        ],
    )


def project_selection(projects: list[dict]) -> Card:
    buttons: list[InlineKeyboardButton] = []
    for p in projects:
        pid = str(p["_id"])
        label = p.get("name", "Untitled")
        buttons.append(btn(label, f"{CallbackPrefix.USER_SELECT_PROJECT}|{pid}"))

    keyboard = InlineKeyboardMarkup(chunk(buttons, per_row=1)) if buttons else None
    return Card(
        title="👋 Welcome",
        body=[
            "Pick a project to open a ticket or leave feedback.",
        ],
        buttons=keyboard,
    )


def project_intro(project: dict) -> Card:
    name = escape_html(project.get("name", "Project"))
    desc = escape_html(project.get("description", ""))
    ptype = project.get("type", "support")
    body: list[str] = []
    if ptype == "feedback":
        body.append("Send your feedback as a message, photo or document.")
        body.append("We read every message.")
    else:
        body.append("Send a message, photo or document to start a support ticket.")
        body.append("Our team will get back to you shortly.")
    return Card(
        title=f"📂 {name}",
        body=body,
        quote=desc if desc else None,
    )


def contact_intro(display_name: str, is_anonymous: bool) -> Card:
    name = escape_html(display_name)
    body = [
        f"You are now connected with <b>{name}</b>.",
        "Send a message to start the conversation.",
    ]
    footer = "<i>Your contact prefers to stay anonymous.</i>" if is_anonymous else None
    return Card(title="📞 Direct contact", body=body, footer=footer)


def ticket_created(
    short_id: str,
    *,
    is_feedback: bool = False,
    is_contact: bool = False,
) -> Card:
    if is_feedback:
        return Card(
            title="✅ Feedback received",
            body=[
                "Thanks for your feedback.",
                "It has been forwarded to our team.",
            ],
        )
    if is_contact:
        return Card(
            title="📞 Message sent",
            body=[
                f"Reference: <code>#{short_id}</code>",
                "Your contact has been notified and will reply here.",
            ],
        )
    return Card(
        title=f"🎫 Ticket #{short_id} created",
        body=[
            f"Reference: <code>#{short_id}</code>",
            "Our support team has been notified.",
            "You can keep writing here to add more details.",
        ],
    )


def cooldown_card(retry_after_sec: int) -> Card:
    return Card(
        title="⚠️ Slow down",
        body=[
            "You are sending messages too quickly.",
            f"Please wait <b>{retry_after_sec}s</b> before trying again.",
        ],
    )


def blocked_silent_card() -> Card:
    # Not sent — blocked users receive nothing.
    return Card(title="🚫 Blocked", body=["Your messages are currently not delivered."])


def please_start_card() -> Card:
    return Card(
        title="⚠️ No active session",
        body=[
            "Open the menu with /start to choose a project first.",
        ],
    )


def rating_card(project_id: str) -> Card:
    buttons = [btn(f"{i} ⭐", f"{CallbackPrefix.USER_RATE}|{project_id}|{i}") for i in range(1, 6)]
    keyboard = InlineKeyboardMarkup([buttons])
    return Card(
        title="⭐ Rate your experience",
        body=["How would you rate this interaction?"],
        buttons=keyboard,
    )


def rating_thanks(score: int) -> Card:
    stars = "⭐" * score
    return Card(
        title="✨ Thanks for your rating",
        body=[stars, "We appreciate your feedback."],
    )


def ticket_closed(short_id: str, *, closed_by_user: bool) -> Card:
    if closed_by_user:
        body = [
            f"Ticket <code>#{short_id}</code> has been closed.",
            "If you need more help, just send a new message.",
        ]
    else:
        body = [
            f"Ticket <code>#{short_id}</code> has been closed by support.",
            "If the issue comes back, send a new message.",
        ]
    return Card(title="✅ Ticket closed", body=body)


def auto_closed_card(short_id: str, days: int) -> Card:
    return Card(
        title="✅ Ticket auto-closed",
        body=[
            f"Ticket <code>#{short_id}</code> was closed after {days} days of inactivity.",
            "Send a new message any time to open a fresh ticket.",
        ],
    )


def history_card(user_id: int, tickets: Sequence[dict]) -> Card:
    if not tickets:
        return Card(title="📜 History", body=["No tickets found for this user."])
    lines: list[str] = []
    for t in tickets[:10]:
        status = "🟢 open" if t.get("status") == "open" else "🔴 closed"
        short = str(t["_id"])[-6:]
        created = t.get("created_at")
        created_fmt = created.strftime("%Y-%m-%d") if created else "?"
        lines.append(f"<code>#{short}</code> • {status} • {created_fmt}")
    return Card(
        title=f"📜 History • user <code>{user_id}</code>",
        body=lines,
        footer=f"<i>Showing {min(len(tickets), 10)} of {len(tickets)}.</i>",
    )


def admin_reply_card(text: str) -> Card:
    return Card(
        title="💬 Support reply",
        quote=escape_html(text),
        quote_expandable=True,
    )


def assignment_notification(short_id: str, project_name: str) -> Card:
    return Card(
        title="📌 Ticket assigned",
        body=[
            f"You have been assigned Ticket <code>#{short_id}</code>.",
            f"Project: <b>{escape_html(project_name)}</b>",
        ],
        footer="<i>Reply in the topic to respond to the user.</i>",
    )


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
