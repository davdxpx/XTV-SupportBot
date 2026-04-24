"""Team domain model.

A team owns a queue of tickets. Tickets are routed to a team by queue
rules (see Phase 5c) and members of the team pick them up via
``/queue`` / ``/mytickets``. Business hours and holidays control SLA
accumulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from xtv_support.domain.enums import Weekday


@dataclass(frozen=True, slots=True, kw_only=True)
class BusinessHoursWindow:
    """A single open window: e.g. ``09:00 - 18:00`` on Monday."""

    weekday: Weekday
    start: str  # ``HH:MM`` in the team timezone
    end: str  # ``HH:MM`` in the team timezone


@dataclass(frozen=True, slots=True, kw_only=True)
class QueueRule:
    """Declarative routing rule matched in registration order."""

    #: Matcher dict — any of ``{tag, project_id, priority, project_type}``.
    match: dict[str, str] = field(default_factory=dict)
    #: Higher weight wins when several rules match; ties broken by rule order.
    weight: int = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class Team:
    """Immutable in-memory Team representation."""

    id: str  # slug, e.g. "support-tier1"
    name: str
    timezone: str = "UTC"
    business_hours: tuple[BusinessHoursWindow, ...] = ()
    holidays: tuple[str, ...] = ()  # ISO dates YYYY-MM-DD
    member_ids: tuple[int, ...] = ()
    queue_rules: tuple[QueueRule, ...] = ()
    created_by: int | None = None
    created_at: datetime | None = None

    def has_member(self, user_id: int) -> bool:
        return user_id in self.member_ids
