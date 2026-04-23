"""Discord formatter tests."""
from __future__ import annotations

from xtv_support.domain.events import (
    SlaBreached,
    SlaWarned,
    TicketAssigned,
    TicketClosed,
    TicketCreated,
    TicketReopened,
)
from xtv_support.services.bridges.discord import build_payload, embed_for


def test_ticket_created_embed() -> None:
    e = TicketCreated(ticket_id="t1", user_id=99, project_id="P1")
    p = build_payload(e)
    assert p is not None
    embed = p["embeds"][0]
    assert "#t1" in embed["title"]
    assert embed["color"] > 0


def test_ticket_assigned_shows_clear_when_none() -> None:
    e = TicketAssigned(ticket_id="t1", assignee_id=None, assigned_by=42)
    embed = embed_for(e)
    assert embed is not None
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Assignee"] == "cleared"


def test_ticket_closed_embed_has_reason() -> None:
    e = TicketClosed(ticket_id="t1", closed_by=42, reason="resolved")
    embed = embed_for(e)
    assert embed is not None
    assert "resolved" in embed["description"]


def test_ticket_reopened_uses_warn_colour() -> None:
    e = TicketReopened(ticket_id="t1", reopened_by=42)
    embed = embed_for(e)
    assert embed is not None
    # warn colour = 15_844_367 (#f1c40f)
    assert embed["color"] == 15_844_367


def test_sla_breached_shows_minutes() -> None:
    e = SlaBreached(ticket_id="t1", age_seconds=9000, breach_after_seconds=7200)
    embed = embed_for(e)
    assert embed is not None
    assert "150m" in embed["description"]   # 9000 / 60


def test_unbridged_event_returns_none() -> None:
    e = SlaWarned(ticket_id="t1", age_seconds=100, warn_after_seconds=60)
    assert build_payload(e) is None
