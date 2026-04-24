"""Base class for every in-process domain event.

Events are immutable, keyword-only dataclasses. Subclasses add their own
required fields after the common metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _new_event_id() -> str:
    return str(uuid.uuid4())


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Common metadata for every published event."""

    event_id: str = field(default_factory=_new_event_id)
    occurred_at: datetime = field(default_factory=_now_utc)
