"""SLA breach / warning events."""
from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class SlaWarned(DomainEvent):
    """First SLA-threshold crossed without an admin reply."""

    ticket_id: str
    age_seconds: int
    warn_after_seconds: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SlaBreached(DomainEvent):
    """Second SLA-threshold crossed — treated as a breach."""

    ticket_id: str
    age_seconds: int
    breach_after_seconds: int
