from __future__ import annotations

from pyrogram.types import InlineKeyboardMarkup

from app.constants import CallbackPrefix
from app.ui.card import Card
from app.ui.keyboards import btn, rows


def _step(
    step: int,
    total: int,
    *,
    status: str,
    body: list[str],
    buttons: InlineKeyboardMarkup | None = None,
) -> Card:
    return Card(
        title="✨ New Project",
        steps=(step, total),
        status_line=status,
        body=body,
        buttons=buttons,
    )


def ask_name() -> Card:
    return _step(1, 4, status="Name", body=[
        "Send the project name.",
        "<i>Send /cancel to abort.</i>",
    ])


def ask_description() -> Card:
    return _step(2, 4, status="Description", body=[
        "Send a short description.",
        "<i>/cancel to abort.</i>",
    ])


def ask_type() -> Card:
    buttons = rows(
        [
            btn("🎫 Support", f"{CallbackPrefix.ADMIN_PROJECT_TYPE}|support"),
            btn("💬 Feedback", f"{CallbackPrefix.ADMIN_PROJECT_TYPE}|feedback"),
        ],
    )
    return _step(
        3,
        4,
        status="Type",
        body=[
            "<b>Support</b>: opens a ticket topic per user.",
            "<b>Feedback</b>: submissions go to a single collection topic.",
        ],
        buttons=buttons,
    )


def ask_rating() -> Card:
    buttons = rows(
        [
            btn("✅ Yes", f"{CallbackPrefix.ADMIN_PROJECT_RATING}|yes"),
            btn("❌ No", f"{CallbackPrefix.ADMIN_PROJECT_RATING}|no"),
        ],
    )
    return _step(4, 4, status="Rating", body=["Enable star ratings?"], buttons=buttons)


def ask_text() -> Card:
    buttons = rows(
        [
            btn("✅ Yes", f"{CallbackPrefix.ADMIN_PROJECT_TEXT}|yes"),
            btn("❌ No", f"{CallbackPrefix.ADMIN_PROJECT_TEXT}|no"),
        ],
    )
    return _step(4, 4, status="Text feedback", body=["Accept free-text feedback?"], buttons=buttons)


def ask_topic_id() -> Card:
    return _step(
        4,
        4,
        status="Feedback topic id",
        body=[
            "Send the numeric <b>topic id</b> that should collect feedback for this project.",
            "You can copy it from the admin forum group.",
        ],
    )


def done_support(name: str) -> Card:
    return Card(title="🎉 Project created", body=[f"Support project <b>{name}</b> is live."])


def done_feedback(name: str) -> Card:
    return Card(title="🎉 Project created", body=[f"Feedback project <b>{name}</b> is live."])


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
