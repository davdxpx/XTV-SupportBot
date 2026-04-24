"""CSAT survey events."""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class CsatPrompted(DomainEvent):
    """DM sent to the user asking for a rating."""

    ticket_id: str
    user_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CsatReceived(DomainEvent):
    """User responded with a star rating (1-5)."""

    ticket_id: str
    user_id: int
    score: int  # 1..5
    team_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CsatCommented(DomainEvent):
    """Optional free-text follow-up after the rating."""

    ticket_id: str
    user_id: int
    score: int
    comment: str
