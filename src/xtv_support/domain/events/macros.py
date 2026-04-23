"""Macro-usage events."""
from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class MacroUsed(DomainEvent):
    """An agent inserted a canned reply into a ticket topic."""

    macro_id: str
    macro_name: str
    ticket_id: str
    actor_id: int
    team_id: str | None = None
