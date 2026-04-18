from __future__ import annotations

from typing import Sequence

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.constants import CallbackPrefix
from app.ui.card import Card
from app.ui.glyphs import DIVIDER, OK, TICKET, WARN
from app.ui.keyboards import btn, chunk
from app.utils.text import escape_html


def welcome_no_projects() -> Card:
    return Card(
        title="Welcome",
        body=[
            "There are currently no active projects.",
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
        title="Welcome",
        body=[
            "Select a project to open a ticket or submit feedback.",
        ],
        buttons=keyboard,
    )


def project_intro(project: dict) -> Card:
    name = escape_html(project.get("name", "Project"))
    desc = escape_html(project.get("description", ""))
    ptype = project.get("type", "support")
    lines: list[str] = []
    if desc:
        lines.append(desc)
        lines.append("")
    if ptype == "feedback":
        lines.append("Send your feedback as a message, photo or document.")
        lines.append("We read every message.")
    else:
        lines.append("Send a message, photo or document to start a support ticket.")
        lines.append("You will be connected with our support team shortly.")
    return Card(title=f"{name}", body=lines)


def contact_intro(display_name: str, is_anonymous: bool) -> Card:
    name = escape_html(display_name)
    lines = [
        f"You are now connected with {name}.",
        "Send a message to start the conversation.",
    ]
    if is_anonymous:
        lines.append("")
        lines.append("Note: your contact prefers to stay anonymous.")
    return Card(title="Direct Contact", body=lines)


def ticket_created(short_id: str, *, is_feedback: bool = False) -> Card:
    if is_feedback:
        body = [
            "Thanks for your feedback.",
            "It has been forwarded to our team.",
        ]
        title = f"{OK}  Feedback received"
    else:
        body = [
            f"Reference: #{short_id}",
            "",
            "Our support team has been notified.",
            "You can keep writing here to add more details.",
        ]
        title = f"{TICKET}  Ticket #{short_id} created"
    return Card(title=title, body=body)


def cooldown_card(retry_after_sec: int) -> Card:
    return Card(
        title=f"{WARN}  Slow down",
        body=[
            "You are sending messages too quickly.",
            f"Please wait {retry_after_sec}s before trying again.",
        ],
    )


def blocked_silent_card() -> Card:
    # Intentionally not sent — blocked users receive nothing.
    return Card(title="Blocked", body=["Your messages are currently not delivered."])


def please_start_card() -> Card:
    return Card(
        title=f"{WARN}  No active session",
        body=[
            "Open the menu with /start to choose a project first.",
        ],
    )


def rating_card(project_id: str) -> Card:
    buttons = [
        btn(f"{i} \u2605", f"{CallbackPrefix.USER_RATE}|{project_id}|{i}")
        for i in range(1, 6)
    ]
    keyboard = InlineKeyboardMarkup([buttons])
    return Card(
        title="Rate your experience",
        body=["How would you rate this interaction?"],
        buttons=keyboard,
    )


def rating_thanks(score: int) -> Card:
    stars = "\u2b50" * score
    return Card(
        title="Thanks for your rating",
        body=[stars, "", "We appreciate your feedback."],
    )


def ticket_closed(short_id: str, *, closed_by_user: bool) -> Card:
    if closed_by_user:
        body = [
            f"Ticket #{short_id} has been closed.",
            "If you need more help, just send a new message.",
        ]
    else:
        body = [
            f"Ticket #{short_id} has been closed by support.",
            "If the issue comes back, send a new message.",
        ]
    return Card(title=f"{OK}  Ticket closed", body=body)


def auto_closed_card(short_id: str, days: int) -> Card:
    return Card(
        title=f"{OK}  Ticket auto-closed",
        body=[
            f"Ticket #{short_id} was closed after {days} days of inactivity.",
            "Send a new message any time to open a fresh ticket.",
        ],
    )


def history_card(user_id: int, tickets: Sequence[dict]) -> Card:
    if not tickets:
        return Card(title="History", body=["No tickets found for this user."])
    lines: list[str] = []
    for t in tickets[:10]:
        status = "open" if t.get("status") == "open" else "closed"
        short = str(t["_id"])[-6:]
        created = t.get("created_at")
        created_fmt = created.strftime("%Y-%m-%d") if created else "?"
        lines.append(f"#{short} \u2022 {status} \u2022 {created_fmt}")
    return Card(
        title=f"History \u2022 user <code>{user_id}</code>",
        body=lines,
        footer=f"Showing {min(len(tickets), 10)} of {len(tickets)}.",
    )


def admin_reply_card(text: str) -> Card:
    return Card(title="Support reply", body=[escape_html(text)])


def assignment_notification(short_id: str, project_name: str) -> Card:
    return Card(
        title="Ticket assigned",
        body=[
            f"You have been assigned Ticket #{short_id}.",
            f"Project: {escape_html(project_name)}",
        ],
        footer="Reply in the topic to respond to the user.",
    )


def divider_line() -> str:
    return DIVIDER

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
