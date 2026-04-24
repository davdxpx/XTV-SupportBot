"""Domain event shape tests — frozen, kw-only, sane defaults."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from xtv_support.domain.events import (
    BroadcastStarted,
    DomainEvent,
    SlaBreached,
    TicketAssigned,
    TicketCreated,
    TicketRoutedToTeam,
    UserBlocked,
)


def test_every_event_auto_assigns_id_and_timestamp() -> None:
    e = TicketCreated(ticket_id="t1", user_id=7)
    # event_id is a valid UUID4 string
    uuid.UUID(e.event_id)
    assert e.occurred_at.tzinfo is UTC or e.occurred_at.tzinfo is not None
    assert e.occurred_at <= datetime.now(UTC)


def test_events_are_frozen() -> None:
    e = TicketAssigned(ticket_id="t1", assignee_id=42, assigned_by=1)
    with pytest.raises(Exception):  # dataclasses raise FrozenInstanceError (subclass of AttrError)
        e.ticket_id = "other"  # type: ignore[misc]


def test_events_are_kw_only() -> None:
    # Positional init must fail for a kw-only dataclass.
    with pytest.raises(TypeError):
        TicketCreated("t1", 7)  # type: ignore[call-arg]


def test_ticket_routed_uses_tuple_default() -> None:
    e = TicketRoutedToTeam(ticket_id="t1", team_id="support-tier1")
    assert e.matched_rules == ()


def test_broadcast_finished_import_from_events_package() -> None:
    # Validates that __init__.py re-exports land correctly.
    e = BroadcastStarted(broadcast_id="b1", initiated_by=1, total_recipients=100)
    assert e.total_recipients == 100


def test_sla_breached_fields() -> None:
    e = SlaBreached(ticket_id="t1", age_seconds=9000, breach_after_seconds=7200)
    assert e.age_seconds > e.breach_after_seconds


def test_user_blocked_reason_optional() -> None:
    e1 = UserBlocked(user_id=1, actor_id=2)
    e2 = UserBlocked(user_id=1, actor_id=2, reason="spam")
    assert e1.reason is None
    assert e2.reason == "spam"


def test_domain_event_is_abstractish_without_extra_fields() -> None:
    # You can instantiate it directly (not abstract in the ABC sense),
    # but typically subclasses carry the actual payload.
    e = DomainEvent()
    uuid.UUID(e.event_id)
