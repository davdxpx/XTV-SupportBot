"""Unit tests for the ticket-header keyboard builders (Phase B).

These assert the callback-data wiring for the in-place pickers so a rename or
reshuffle can't silently break the header controls. Imports pyrogram (via the
builders' InlineKeyboardMarkup), so this runs on CI, not the sandbox.
"""

from __future__ import annotations

from xtv_support.core.constants import CallbackPrefix as CP
from xtv_support.ui.templates.ticket_header import (
    action_rows,
    assign_rows,
    confirm_close_rows,
    priority_rows,
    tag_rows,
)

TID = "656d0f0f0f0f0f0f0f0f0f0f"


def _flat(markup):
    return [b for row in markup.inline_keyboard for b in row]


def _data(markup):
    return [b.callback_data for b in _flat(markup)]


def test_action_rows_default_four() -> None:
    data = _data(action_rows(TID))
    assert data == [
        f"{CP.TICKET_ASSIGN}|{TID}",
        f"{CP.TICKET_TAG}|{TID}",
        f"{CP.TICKET_PRIORITY}|{TID}",
        f"{CP.TICKET_CLOSE}|{TID}",
    ]


def test_assign_rows_has_picks_unassign_and_back() -> None:
    data = _data(assign_rows(TID, [("Ann", 1), ("Bob", 2)]))
    assert f"{CP.TICKET_ASSIGN_PICK}|{TID}|1" in data
    assert f"{CP.TICKET_ASSIGN_PICK}|{TID}|2" in data
    assert f"{CP.TICKET_ASSIGN_PICK}|{TID}|0" in data  # Unassign
    assert data[-1] == f"{CP.TICKET_ACTIONS}|{TID}"  # Back


def test_tag_rows_markers_and_done() -> None:
    markup = tag_rows(TID, ["bug", "vip"], {"bug"})
    labels = [b.text for b in _flat(markup)]
    assert "✓ #bug" in labels
    assert "• #vip" in labels
    data = _data(markup)
    assert f"{CP.TICKET_TAG_TOGGLE}|{TID}|bug" in data
    assert data[-1] == f"{CP.TICKET_ACTIONS}|{TID}"  # Done → back


def test_priority_rows_choices_and_back() -> None:
    data = _data(priority_rows(TID))
    assert f"{CP.TICKET_PRIORITY_PICK}|{TID}|low" in data
    assert f"{CP.TICKET_PRIORITY_PICK}|{TID}|normal" in data
    assert f"{CP.TICKET_PRIORITY_PICK}|{TID}|high" in data
    assert f"{CP.TICKET_ACTIONS}|{TID}" in data


def test_confirm_close_rows() -> None:
    data = _data(confirm_close_rows(TID))
    assert data[0] == f"{CP.TICKET_CLOSE_CONFIRM}|{TID}"
    assert data[-1] == f"{CP.TICKET_ACTIONS}|{TID}"
