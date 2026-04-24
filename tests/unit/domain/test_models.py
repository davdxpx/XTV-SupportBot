"""Role / Team dataclass model tests."""

from __future__ import annotations

import pytest

from xtv_support.domain.enums import Role, Weekday
from xtv_support.domain.models.role import RoleAssignment
from xtv_support.domain.models.team import BusinessHoursWindow, QueueRule, Team


# --------------------------------------------------------------------------
# RoleAssignment
# --------------------------------------------------------------------------
def test_role_assignment_is_frozen() -> None:
    a = RoleAssignment(user_id=1, role=Role.ADMIN)
    with pytest.raises(Exception):
        a.user_id = 2  # type: ignore[misc]


def test_belongs_to_team() -> None:
    a = RoleAssignment(user_id=1, role=Role.AGENT, team_ids=("t1", "t2"))
    assert a.belongs_to_team("t1")
    assert not a.belongs_to_team("nope")


def test_role_assignment_default_team_ids_is_empty_tuple() -> None:
    a = RoleAssignment(user_id=1, role=Role.VIEWER)
    assert a.team_ids == ()


# --------------------------------------------------------------------------
# Team
# --------------------------------------------------------------------------
def test_team_has_member() -> None:
    t = Team(id="support", name="Support", member_ids=(1, 2, 3))
    assert t.has_member(2)
    assert not t.has_member(42)


def test_team_is_frozen() -> None:
    t = Team(id="s", name="Support")
    with pytest.raises(Exception):
        t.name = "new"  # type: ignore[misc]


def test_team_holds_queue_rules() -> None:
    rules = (
        QueueRule(match={"tag": "billing"}, weight=200),
        QueueRule(match={"project_type": "feedback"}, weight=50),
    )
    t = Team(id="s", name="Support", queue_rules=rules)
    assert len(t.queue_rules) == 2
    assert t.queue_rules[0].weight == 200


def test_team_holds_business_hours() -> None:
    t = Team(
        id="s",
        name="Support",
        timezone="Europe/Berlin",
        business_hours=(
            BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="18:00"),
            BusinessHoursWindow(weekday=Weekday.FRIDAY, start="09:00", end="15:00"),
        ),
    )
    assert t.business_hours[0].weekday is Weekday.MONDAY
    assert t.business_hours[1].end == "15:00"


def test_team_defaults_are_empty() -> None:
    t = Team(id="s", name="Support")
    assert t.timezone == "UTC"
    assert t.business_hours == ()
    assert t.holidays == ()
    assert t.member_ids == ()
    assert t.queue_rules == ()
