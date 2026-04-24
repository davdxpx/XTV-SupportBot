"""Project-template registry + runner tests."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from xtv_support.services.templates import default_registry, install_template
from xtv_support.services.templates.builtins import ALL as BUILTINS
from xtv_support.services.templates.model import ProjectTemplate, MacroSeed


def _run(coro):
    return asyncio.run(coro)


def test_all_builtins_are_registered() -> None:
    slugs = default_registry.slugs()
    for tmpl in BUILTINS:
        assert tmpl.slug in slugs
    # deterministic ordering
    assert slugs == tuple(sorted(slugs))


def test_builtin_slugs_are_unique() -> None:
    slugs = [t.slug for t in BUILTINS]
    assert len(slugs) == len(set(slugs))


def test_every_builtin_has_required_metadata() -> None:
    for tmpl in BUILTINS:
        assert tmpl.slug
        assert tmpl.name
        assert tmpl.description
        assert tmpl.icon
        assert tmpl.project_type in {"support", "feedback", "contact"}


def test_register_rejects_empty_slug() -> None:
    from xtv_support.services.templates.registry import TemplateRegistry

    reg = TemplateRegistry()
    with pytest.raises(ValueError):
        reg.register(
            ProjectTemplate(
                slug="",
                name="x",
                description="y",
            )
        )


class _Bus:
    def __init__(self) -> None:
        self.published: list[Any] = []

    async def publish(self, event: Any) -> None:
        self.published.append(event)


class _FakeColl:
    def __init__(self, name: str) -> None:
        self.name = name
        self.docs: list[dict] = []
        self.upserts: list[tuple[dict, dict]] = []

    async def find_one(self, filt: dict, projection: dict | None = None) -> dict | None:
        for d in self.docs:
            if all(d.get(k) == v for k, v in filt.items()):
                return d
        return None

    async def insert_one(self, doc: dict) -> Any:
        from bson import ObjectId  # lazy — only used when available

        doc = {"_id": ObjectId(), **doc}
        self.docs.append(doc)

        class _R:
            inserted_id = doc["_id"]

        return _R()

    async def update_one(self, filt: dict, update: dict, **kw: Any) -> Any:
        self.upserts.append((filt, update))

        class _R:
            matched_count = 1

        return _R()


class _FakeDB:
    def __init__(self) -> None:
        self.projects = _FakeColl("projects")
        self.macros = _FakeColl("macros")
        self.kb_articles = _FakeColl("kb_articles")


def test_install_happy_path_seeds_everything() -> None:
    pytest.importorskip("bson")
    db = _FakeDB()
    bus = _Bus()

    tmpl = ProjectTemplate(
        slug="minitest",
        name="Mini Test",
        description="x",
        macros=(MacroSeed(name="hi", body="hello"),),
    )

    result = _run(
        install_template(
            db,
            bus,
            template=tmpl,
            project_slug="mt",
            installed_by=42,
        )
    )

    assert result.ok, result.detail
    assert result.macros_seeded == 1
    assert len(db.projects.docs) == 1
    assert db.projects.docs[0]["template_slug"] == "minitest"
    assert any(e.__class__.__name__ == "ProjectTemplateInstalled" for e in bus.published)
