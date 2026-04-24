"""Macro (canned-response) domain model.

A macro is a named reusable reply that agents insert into a ticket
topic with ``/macro use <name>``. Team-scoped macros are only visible
to members of that team; macros with ``team_id=None`` are global.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Macro:
    """Immutable in-memory representation of a macro."""

    id: str  # Mongo ObjectId as str
    name: str  # slug-ish: [a-z0-9_-]{1,32}
    body: str  # HTML-safe reply template
    team_id: str | None = None  # None -> global
    tags: tuple[str, ...] = ()
    usage_count: int = 0
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def scope(self) -> str:
        return "global" if self.team_id is None else f"team:{self.team_id}"
