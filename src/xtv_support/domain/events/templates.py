"""Project-template events."""

from __future__ import annotations

from dataclasses import dataclass, field

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTemplateInstalled(DomainEvent):
    template_slug: str
    project_slug: str
    project_id: str
    installed_by: int
    macros_seeded: int = 0
    kb_articles_seeded: int = 0
    routing_rules_seeded: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTemplateFailed(DomainEvent):
    template_slug: str
    project_slug: str
    attempted_by: int
    error: str
