"""Domain enum tests — Role hierarchy, Priority ranks, parser."""
from __future__ import annotations

import pytest

from xtv_support.domain.enums import Priority, Role, TicketStatus, Weekday


def test_role_ranks_ascend() -> None:
    order = [
        Role.USER, Role.VIEWER, Role.AGENT,
        Role.SUPERVISOR, Role.ADMIN, Role.OWNER,
    ]
    ranks = [r.rank for r in order]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)  # unique


@pytest.mark.parametrize(
    "who,required,expected",
    [
        (Role.OWNER, Role.ADMIN, True),
        (Role.ADMIN, Role.ADMIN, True),
        (Role.SUPERVISOR, Role.ADMIN, False),
        (Role.AGENT, Role.SUPERVISOR, False),
        (Role.USER, Role.VIEWER, False),
        (Role.AGENT, Role.USER, True),
    ],
)
def test_role_can_follows_hierarchy(who: Role, required: Role, expected: bool) -> None:
    assert who.can(required) is expected


def test_from_string_known_value() -> None:
    assert Role.from_string("admin") is Role.ADMIN
    assert Role.from_string("  AGENT ") is Role.AGENT


def test_from_string_unknown_falls_back_to_user() -> None:
    assert Role.from_string("pirate") is Role.USER
    assert Role.from_string(None) is Role.USER


def test_from_string_respects_default() -> None:
    assert Role.from_string("pirate", default=Role.VIEWER) is Role.VIEWER


def test_priority_ranks_ascend() -> None:
    order = [Priority.LOW, Priority.NORMAL, Priority.HIGH, Priority.URGENT]
    assert [p.rank for p in order] == [0, 1, 2, 3]


def test_weekday_is_iso_monday_zero() -> None:
    assert int(Weekday.MONDAY) == 0
    assert int(Weekday.SUNDAY) == 6


def test_ticket_status_values() -> None:
    assert {s.value for s in TicketStatus} == {"open", "pending", "closed"}
