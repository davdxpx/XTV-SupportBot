"""Escalation-rule domain model.

Each rule maps a *trigger* condition (``when``) to an *action block*
(``do``). Rules are evaluated on matching domain events; the first
matching rule whose cooldown has lapsed fires its action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class EscalationWhen:
    """Trigger filter. All provided fields must match (AND)."""

    event: str  # "sla_breached" | "ticket_tagged" | "ticket_created"
    tag: str | None = None  # only consider tickets with this tag
    priority: str | None = None  # only consider this priority
    project_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class EscalationDo:
    """Action block. Any subset may be set."""

    reassign_to: str | None = None  # team slug
    notify_role: str | None = None  # Role.value to DM
    raise_priority: str | None = None  # Priority.value to set on the ticket


@dataclass(frozen=True, slots=True, kw_only=True)
class EscalationRule:
    """A single rule as stored in ``escalation_rules``."""

    id: str
    name: str
    when: EscalationWhen
    do: EscalationDo
    cooldown_s: int = 300  # minimum seconds between fires per ticket
    team_id: str | None = None  # None means "global"
    enabled: bool = True
    created_by: int | None = None
    created_at: datetime | None = None
