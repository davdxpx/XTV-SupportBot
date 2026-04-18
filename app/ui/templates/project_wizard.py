from __future__ import annotations

from pyrogram.types import InlineKeyboardMarkup

from app.constants import CallbackPrefix
from app.ui.card import Card
from app.ui.keyboards import btn, rows
from app.ui.progress import bar as progress_bar


def step_card(
    step: int,
    total: int,
    *,
    status: str,
    body: list[str],
    buttons: InlineKeyboardMarkup | None = None,
) -> Card:
    pct = step / total if total else 0
    footer_lines = [f"Progress: {pct*100:.0f}%", progress_bar(pct)]
    return Card(
        title="New Project",
        steps=(step, total),
        status_line=status,
        body=body,
        footer="\n".join(footer_lines),
        buttons=buttons,
    )


def ask_name() -> Card:
    return step_card(1, 4, status="Name", body=["Send the project name.", "Send /cancel to abort."])


def ask_description() -> Card:
    return step_card(
        2, 4, status="Description", body=["Send a short description.", "Send /cancel to abort."]
    )


def ask_type() -> Card:
    buttons = rows(
        [
            btn("Support", f"{CallbackPrefix.ADMIN_PROJECT_TYPE}|support"),
            btn("Feedback", f"{CallbackPrefix.ADMIN_PROJECT_TYPE}|feedback"),
        ],
    )
    return step_card(
        3,
        4,
        status="Type",
        body=[
            "Support: opens a ticket topic per user.",
            "Feedback: submissions go to a single collection topic.",
        ],
        buttons=buttons,
    )


def ask_rating() -> Card:
    buttons = rows(
        [
            btn("Yes", f"{CallbackPrefix.ADMIN_PROJECT_RATING}|yes"),
            btn("No", f"{CallbackPrefix.ADMIN_PROJECT_RATING}|no"),
        ],
    )
    return step_card(4, 4, status="Rating", body=["Enable star ratings?"], buttons=buttons)


def ask_text() -> Card:
    buttons = rows(
        [
            btn("Yes", f"{CallbackPrefix.ADMIN_PROJECT_TEXT}|yes"),
            btn("No", f"{CallbackPrefix.ADMIN_PROJECT_TEXT}|no"),
        ],
    )
    return step_card(4, 4, status="Text feedback", body=["Accept free-text feedback?"], buttons=buttons)


def ask_topic_id() -> Card:
    return step_card(
        4,
        4,
        status="Feedback topic id",
        body=[
            "Send the numeric <b>topic id</b> that should collect feedback for this project.",
            "You can copy it from the admin forum group.",
        ],
    )


def done_support(name: str) -> Card:
    return Card(title="Project Created", body=[f"Support project <b>{name}</b> is live."])


def done_feedback(name: str) -> Card:
    return Card(title="Project Created", body=[f"Feedback project <b>{name}</b> is live."])
