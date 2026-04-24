"""Ticket-lifecycle events."""

from __future__ import annotations

from dataclasses import dataclass, field

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class TicketCreated(DomainEvent):
    ticket_id: str
    user_id: int
    project_id: str | None = None
    topic_id: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class TicketAssigned(DomainEvent):
    ticket_id: str
    assignee_id: int | None  # ``None`` means the assignee was cleared
    assigned_by: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TicketTagged(DomainEvent):
    ticket_id: str
    tags_added: tuple[str, ...] = ()
    tags_removed: tuple[str, ...] = ()
    actor_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TicketPriorityChanged(DomainEvent):
    ticket_id: str
    priority: str
    actor_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TicketClosed(DomainEvent):
    ticket_id: str
    closed_by: int
    reason: str = "manual"  # manual | autoclose | resolved


@dataclass(frozen=True, slots=True, kw_only=True)
class TicketReopened(DomainEvent):
    ticket_id: str
    reopened_by: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TicketRoutedToTeam(DomainEvent):
    """Fired after queue-routing decides the owning team (Phase 5)."""

    ticket_id: str
    team_id: str
    reason: str = "auto"
    matched_rules: tuple[str, ...] = field(default_factory=tuple)
