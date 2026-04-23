"""Project-management events."""
from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCreated(DomainEvent):
    project_id: str
    name: str
    type: str  # support | feedback | contact
    created_by: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectDeleted(DomainEvent):
    project_id: str
    deleted_by: int
