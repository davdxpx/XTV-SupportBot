"""Dry-run: evaluate a rule's conditions against a ticket without executing."""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.services.rules.model import Rule, condition_matches


@dataclass(frozen=True, slots=True)
class ConditionEvaluation:
    field: str
    op: str
    value: object
    matched: bool


@dataclass(frozen=True, slots=True)
class DryRunResult:
    rule_id: str
    would_fire: bool
    conditions: tuple[ConditionEvaluation, ...]


def dry_run(rule: Rule, ticket: dict) -> DryRunResult:
    evals = tuple(
        ConditionEvaluation(
            field=c.field, op=c.op, value=c.value, matched=condition_matches(c, ticket)
        )
        for c in rule.conditions
    )
    would_fire = all(e.matched for e in evals) if evals else True
    return DryRunResult(rule_id=rule.id, would_fire=would_fire, conditions=evals)
