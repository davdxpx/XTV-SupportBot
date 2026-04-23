"""Broadcast-lifecycle events."""
from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class BroadcastStarted(DomainEvent):
    broadcast_id: str
    initiated_by: int
    total_recipients: int


@dataclass(frozen=True, slots=True, kw_only=True)
class BroadcastPaused(DomainEvent):
    broadcast_id: str
    actor_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class BroadcastResumed(DomainEvent):
    broadcast_id: str
    actor_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class BroadcastCancelled(DomainEvent):
    broadcast_id: str
    actor_id: int
    delivered: int
    failed: int


@dataclass(frozen=True, slots=True, kw_only=True)
class BroadcastFinished(DomainEvent):
    broadcast_id: str
    delivered: int
    failed: int
    duration_seconds: float
