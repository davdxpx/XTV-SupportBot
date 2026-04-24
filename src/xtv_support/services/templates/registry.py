"""Name-keyed registry of :class:`ProjectTemplate`."""

from __future__ import annotations

from typing import Iterable

from xtv_support.services.templates.model import ProjectTemplate


class TemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, ProjectTemplate] = {}

    def register(self, template: ProjectTemplate) -> None:
        if not template.slug:
            raise ValueError("ProjectTemplate.slug must be non-empty")
        self._templates[template.slug] = template

    def register_many(self, templates: Iterable[ProjectTemplate]) -> None:
        for t in templates:
            self.register(t)

    def get(self, slug: str) -> ProjectTemplate | None:
        return self._templates.get(slug)

    def list(self) -> tuple[ProjectTemplate, ...]:
        return tuple(sorted(self._templates.values(), key=lambda t: t.slug))

    def slugs(self) -> tuple[str, ...]:
        return tuple(sorted(self._templates))


default_registry = TemplateRegistry()
