"""Action-executor events.

These fire whenever :class:`xtv_support.services.actions.executor.ActionExecutor`
runs an action — whether it was triggered from a bulk-action in the
agent cockpit, a single command in a topic, a rule engine evaluation,
or an API call. Keeping one event surface means downstream consumers
(audit log, analytics, webhooks) don't have to care about the origin.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ActionExecuted(DomainEvent):
    action: str
    ticket_id: str | None = None
    actor_id: int | None = None
    origin: str = "unknown"  # "bot" | "api" | "rule" | "bulk"
    params: dict = field(default_factory=dict)
    latency_ms: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class ActionFailed(DomainEvent):
    action: str
    ticket_id: str | None = None
    actor_id: int | None = None
    origin: str = "unknown"
    params: dict = field(default_factory=dict)
    error: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class BulkActionStarted(DomainEvent):
    action: str
    actor_id: int
    ticket_ids: tuple[str, ...]
    origin: str = "bot"


@dataclass(frozen=True, slots=True, kw_only=True)
class BulkActionCompleted(DomainEvent):
    action: str
    actor_id: int
    succeeded: int
    failed: int
    duration_ms: int
