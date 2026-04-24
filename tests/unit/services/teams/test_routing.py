"""Queue-routing engine tests — pure, no DB / bus required."""

from __future__ import annotations

import pytest

from xtv_support.domain.models.team import QueueRule, Team
from xtv_support.services.teams.routing import route_ticket


def _team(tid: str, rules: list[QueueRule]) -> Team:
    return Team(id=tid, name=tid.title(), queue_rules=tuple(rules))


def test_no_teams_returns_none() -> None:
    result = route_ticket({"_id": "t1", "tags": ["x"]}, [])
    assert result.team is None
    assert result.score == 0


def test_no_matching_rule_returns_none() -> None:
    teams = [_team("support", [QueueRule(match={"tag": "vip"}, weight=200)])]
    result = route_ticket({"_id": "t1", "tags": ["regular"]}, teams)
    assert result.team is None


def test_single_team_single_match() -> None:
    teams = [_team("support", [QueueRule(match={"tag": "vip"}, weight=200)])]
    result = route_ticket({"_id": "t1", "tags": ["vip"]}, teams)
    assert result.team is teams[0]
    assert result.score == 200
    assert result.matched_rules == ("tag=vip @ w=200",)


def test_highest_weight_wins() -> None:
    teams = [
        _team("billing", [QueueRule(match={"tag": "billing"}, weight=100)]),
        _team("vip", [QueueRule(match={"tag": "billing"}, weight=500)]),
    ]
    result = route_ticket({"_id": "t1", "tags": ["billing"]}, teams)
    assert result.team.id == "vip"
    assert result.score == 500


def test_same_weight_ties_use_registration_order() -> None:
    teams = [
        _team("first", [QueueRule(match={"tag": "x"}, weight=100)]),
        _team("second", [QueueRule(match={"tag": "x"}, weight=100)]),
    ]
    result = route_ticket({"_id": "t1", "tags": ["x"]}, teams)
    assert result.team.id == "first"


def test_catchall_rule_matches_anything() -> None:
    teams = [_team("support", [QueueRule(match={}, weight=50)])]
    result = route_ticket({"_id": "t1"}, teams)
    assert result.team.id == "support"


def test_catchall_loses_to_specific_match() -> None:
    teams = [
        _team("support", [QueueRule(match={}, weight=50)]),
        _team("billing", [QueueRule(match={"tag": "billing"}, weight=100)]),
    ]
    result = route_ticket({"_id": "t1", "tags": ["billing"]}, teams)
    assert result.team.id == "billing"


def test_and_across_keys_within_a_rule() -> None:
    rule = QueueRule(match={"tag": "vip", "priority": "urgent"}, weight=300)
    teams = [_team("critical", [rule])]

    # Both match -> allowed
    r = route_ticket(
        {"_id": "t1", "tags": ["vip", "other"], "priority": "urgent"},
        teams,
    )
    assert r.team is not None

    # Only tag matches -> no match
    r = route_ticket(
        {"_id": "t2", "tags": ["vip"], "priority": "normal"},
        teams,
    )
    assert r.team is None


def test_unknown_match_key_rejects_the_rule() -> None:
    rule = QueueRule(match={"typo_key": "vip"}, weight=300)
    teams = [_team("support", [rule])]
    r = route_ticket({"_id": "t1", "tags": ["vip"]}, teams)
    assert r.team is None


def test_project_id_and_project_type_matchers() -> None:
    teams = [
        _team("feedback", [QueueRule(match={"project_type": "feedback"}, weight=80)]),
        _team("vip_proj", [QueueRule(match={"project_id": "P42"}, weight=150)]),
    ]
    # project_type match
    r = route_ticket({"_id": "t1", "project_type": "feedback"}, teams)
    assert r.team.id == "feedback"
    # project_id match (higher weight)
    r = route_ticket({"_id": "t2", "project_id": "P42", "project_type": "feedback"}, teams)
    assert r.team.id == "vip_proj"


def test_best_weight_per_team_wins() -> None:
    # Team has two rules that both match; team's score = max of matching weights.
    team = _team(
        "support",
        [
            QueueRule(match={"tag": "a"}, weight=100),
            QueueRule(match={"tag": "b"}, weight=300),
        ],
    )
    r = route_ticket({"_id": "t1", "tags": ["a", "b"]}, [team])
    assert r.team is team
    assert r.score == 300
    # Both rules are recorded in matched_rules.
    assert len(r.matched_rules) == 2


def test_tags_missing_does_not_crash() -> None:
    teams = [_team("x", [QueueRule(match={"tag": "vip"}, weight=100)])]
    result = route_ticket({"_id": "t1"}, teams)
    assert result.team is None


@pytest.mark.parametrize("tag_value", ["vip", ["vip", "other"], ("vip",)])
def test_tag_match_accepts_iterables_and_scalars(tag_value) -> None:
    teams = [_team("vip", [QueueRule(match={"tag": "vip"}, weight=100)])]
    result = route_ticket({"_id": "t1", "tags": tag_value}, teams)
    assert result.team.id == "vip"
