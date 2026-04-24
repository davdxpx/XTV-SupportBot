"""Automation-rule lifecycle events."""

from __future__ import annotations

from dataclasses import dataclass, field

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleCreated(DomainEvent):
    rule_id: str
    name: str
    trigger: str
    created_by: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleUpdated(DomainEvent):
    rule_id: str
    version: int
    updated_by: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleDeleted(DomainEvent):
    rule_id: str
    deleted_by: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleEnabled(DomainEvent):
    rule_id: str
    actor_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleDisabled(DomainEvent):
    rule_id: str
    actor_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleExecuted(DomainEvent):
    rule_id: str
    ticket_id: str | None
    trigger: str
    actions_succeeded: int = 0
    actions_failed: int = 0
    latency_ms: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleSkipped(DomainEvent):
    rule_id: str
    ticket_id: str | None
    trigger: str
    reason: str  # "cooldown" | "cap_reached" | "conditions_unmet"
    details: dict = field(default_factory=dict)
