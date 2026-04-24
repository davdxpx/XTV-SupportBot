"""Escalation-engine tests."""

from __future__ import annotations

from xtv_support.domain.models.escalation import (
    EscalationDo,
    EscalationRule,
    EscalationWhen,
)
from xtv_support.services.escalation.engine import evaluate


def _rule(
    name: str,
    *,
    event: str,
    tag: str | None = None,
    priority: str | None = None,
    project_id: str | None = None,
    team_id: str | None = None,
    enabled: bool = True,
    reassign_to: str | None = None,
    notify_role: str | None = None,
    raise_priority: str | None = None,
) -> EscalationRule:
    return EscalationRule(
        id=name,
        name=name,
        when=EscalationWhen(event=event, tag=tag, priority=priority, project_id=project_id),
        do=EscalationDo(
            reassign_to=reassign_to,
            notify_role=notify_role,
            raise_priority=raise_priority,
        ),
        team_id=team_id,
        enabled=enabled,
    )


# ----------------------------------------------------------------------
# Event filter
# ----------------------------------------------------------------------
def test_event_mismatch_skips_rule() -> None:
    rule = _rule("r", event="sla_breached")
    outcomes = evaluate("ticket_tagged", {}, [rule])
    assert outcomes == []


def test_disabled_rule_never_fires() -> None:
    rule = _rule("r", event="sla_breached", enabled=False)
    outcomes = evaluate("sla_breached", {}, [rule])
    assert outcomes == []


# ----------------------------------------------------------------------
# Tag matching
# ----------------------------------------------------------------------
def test_tag_filter_on_sla_breach_checks_ticket_tags() -> None:
    rule = _rule("vip-breach", event="sla_breached", tag="vip")
    outcomes = evaluate("sla_breached", {"tags": ["vip", "other"]}, [rule])
    assert len(outcomes) == 1
    outcomes = evaluate("sla_breached", {"tags": ["regular"]}, [rule])
    assert outcomes == []


def test_tag_filter_on_tagged_event_uses_added_tag() -> None:
    rule = _rule("vip-add", event="ticket_tagged", tag="vip")
    # ticket already tagged "vip" but tag_added is "other" -> no match.
    outcomes = evaluate("ticket_tagged", {"tags": ["vip"]}, [rule], tag_added="other")
    assert outcomes == []
    # now tag_added matches.
    outcomes = evaluate("ticket_tagged", {"tags": ["vip"]}, [rule], tag_added="vip")
    assert len(outcomes) == 1


# ----------------------------------------------------------------------
# Priority / project filters
# ----------------------------------------------------------------------
def test_priority_filter() -> None:
    rule = _rule("urgent-only", event="sla_breached", priority="urgent")
    assert evaluate("sla_breached", {"priority": "urgent"}, [rule])
    assert not evaluate("sla_breached", {"priority": "normal"}, [rule])


def test_project_filter() -> None:
    rule = _rule("p1-only", event="ticket_created", project_id="P1")
    assert evaluate("ticket_created", {"project_id": "P1"}, [rule])
    assert not evaluate("ticket_created", {"project_id": "P2"}, [rule])


# ----------------------------------------------------------------------
# Team scoping
# ----------------------------------------------------------------------
def test_team_scoped_rule_only_fires_for_that_team() -> None:
    rule = _rule("support-only", event="sla_breached", team_id="support")
    # Ticket belongs to "billing" -> skip.
    outcomes = evaluate("sla_breached", {}, [rule], ticket_team_id="billing")
    assert outcomes == []
    # Matches team.
    outcomes = evaluate("sla_breached", {}, [rule], ticket_team_id="support")
    assert len(outcomes) == 1


def test_global_rule_fires_regardless_of_team() -> None:
    rule = _rule("global", event="sla_breached")  # team_id=None
    assert evaluate("sla_breached", {}, [rule], ticket_team_id="anything")


# ----------------------------------------------------------------------
# Multiple matching rules fire in declared order
# ----------------------------------------------------------------------
def test_multiple_matches_preserve_order() -> None:
    r1 = _rule("r1", event="sla_breached", reassign_to="support")
    r2 = _rule("r2", event="sla_breached", notify_role="admin")
    outcomes = evaluate("sla_breached", {}, [r1, r2])
    assert [o.rule.name for o in outcomes] == ["r1", "r2"]


def test_compound_when_and_do() -> None:
    rule = _rule(
        "vip-urgent",
        event="sla_breached",
        tag="vip",
        priority="urgent",
        reassign_to="vip_team",
        notify_role="admin",
        raise_priority="urgent",
    )
    outcomes = evaluate(
        "sla_breached",
        {"tags": ["vip"], "priority": "urgent"},
        [rule],
    )
    assert len(outcomes) == 1
    assert outcomes[0].rule.do.reassign_to == "vip_team"
    assert outcomes[0].rule.do.notify_role == "admin"
