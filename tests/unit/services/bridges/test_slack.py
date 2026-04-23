"""Slack formatter tests."""
from __future__ import annotations

from xtv_support.domain.events import (
    SlaBreached,
    SlaWarned,
    TicketAssigned,
    TicketClosed,
    TicketCreated,
    TicketReopened,
)
from xtv_support.services.bridges.slack import build_payload


def _only_attachment(payload):
    return payload["attachments"][0]


def test_ticket_created_payload_shape() -> None:
    e = TicketCreated(ticket_id="t1", user_id=99, project_id="P1")
    p = build_payload(e)
    att = _only_attachment(p)
    text = " ".join(
        b["text"]["text"] for b in att["blocks"] if b["type"] == "section"
    )
    assert "t1" in text and "99" in text and "P1" in text
    assert att["color"].startswith("#")


def test_ticket_assigned_mentions_assignee() -> None:
    e = TicketAssigned(ticket_id="t1", assignee_id=42, assigned_by=1)
    att = _only_attachment(build_payload(e))
    text = att["blocks"][0]["text"]["text"]
    assert "42" in text


def test_ticket_assigned_with_none_renders_cleared() -> None:
    e = TicketAssigned(ticket_id="t1", assignee_id=None, assigned_by=1)
    att = _only_attachment(build_payload(e))
    text = att["blocks"][0]["text"]["text"]
    assert "cleared" in text


def test_ticket_closed_contains_reason() -> None:
    e = TicketClosed(ticket_id="t1", closed_by=1, reason="autoclose")
    att = _only_attachment(build_payload(e))
    text = att["blocks"][0]["text"]["text"]
    assert "autoclose" in text


def test_sla_breached_shows_minute_math() -> None:
    e = SlaBreached(ticket_id="t1", age_seconds=9000, breach_after_seconds=7200)
    att = _only_attachment(build_payload(e))
    texts = " ".join(b["text"]["text"] for b in att["blocks"])
    assert "150m" in texts
    assert "120m" in texts


def test_reopened_is_warn_colour() -> None:
    e = TicketReopened(ticket_id="t1", reopened_by=1)
    att = _only_attachment(build_payload(e))
    assert att["color"] == "#f1c40f"


def test_unbridged_event_returns_none() -> None:
    e = SlaWarned(ticket_id="t1", age_seconds=100, warn_after_seconds=60)
    assert build_payload(e) is None
