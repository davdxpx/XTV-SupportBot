from __future__ import annotations

from xtv_support.services.rules.dry_run import dry_run
from xtv_support.services.rules.model import (
    ActionRef,
    Condition,
    Rule,
    all_conditions_match,
    condition_matches,
)


def _rule(*conds: Condition, enabled: bool = True) -> Rule:
    return Rule(
        id="r1",
        name="Test rule",
        enabled=enabled,
        trigger="TicketCreated",
        conditions=tuple(conds),
        actions=(ActionRef(name="tag", params={"tag": "vip"}),),
    )


def test_eq_and_ne_conditions() -> None:
    ticket = {"priority": "high"}
    assert condition_matches(Condition(field="priority", op="eq", value="high"), ticket)
    assert not condition_matches(Condition(field="priority", op="eq", value="low"), ticket)
    assert condition_matches(Condition(field="priority", op="ne", value="low"), ticket)


def test_in_and_not_in_conditions() -> None:
    ticket = {"priority": "high"}
    assert condition_matches(
        Condition(field="priority", op="in", value=["high", "urgent"]), ticket
    )
    assert condition_matches(
        Condition(field="priority", op="not_in", value=["low"]), ticket
    )


def test_contains_list_field() -> None:
    ticket = {"tags": ["billing", "vip"]}
    assert condition_matches(Condition(field="tags", op="contains", value="vip"), ticket)
    assert not condition_matches(
        Condition(field="tags", op="contains", value="unrelated"), ticket
    )


def test_walk_nested_field() -> None:
    ticket = {"meta": {"lang": "en"}}
    assert condition_matches(Condition(field="meta.lang", op="eq", value="en"), ticket)


def test_all_conditions_match_requires_all() -> None:
    ticket = {"priority": "high", "tags": ["billing"]}
    conds = (
        Condition(field="priority", op="eq", value="high"),
        Condition(field="tags", op="contains", value="billing"),
    )
    assert all_conditions_match(conds, ticket)
    # Flip one to false
    conds = (
        Condition(field="priority", op="eq", value="low"),
        Condition(field="tags", op="contains", value="billing"),
    )
    assert not all_conditions_match(conds, ticket)


def test_dry_run_reports_per_condition() -> None:
    ticket = {"priority": "high", "tags": ["billing"]}
    rule = _rule(
        Condition(field="priority", op="eq", value="high"),
        Condition(field="tags", op="contains", value="vip"),  # will fail
    )
    result = dry_run(rule, ticket)
    assert not result.would_fire
    assert [c.matched for c in result.conditions] == [True, False]
