"""Project management routes — id-keyed CRUD, archive/restore, hard delete.

Guards the Phase-2 fix: the SPA sends the project ``_id`` (not slug), so the
routes must key on ``_id`` with a slug fallback, and DELETE must hard-remove.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import security as sec
from xtv_support.infrastructure.db import migrations

_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


@pytest.fixture
def env() -> Iterator[tuple[TestClient, dict]]:
    import os

    os.environ["ADMIN_IDS"] = "1"
    os.environ["WEB_ENABLED"] = "false"

    from xtv_support.config import settings as settings_mod

    saved = settings_mod.settings
    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    db = AsyncMongoMockClient().testdb
    _run(migrations.ensure_indexes(db))
    key = _run(sec.create_key(db, label="k", scopes=["admin:full"], created_by=1)).plaintext

    from xtv_support.api.server import create_app

    client = TestClient(create_app(db=db))
    yield client, {"Authorization": f"Bearer {key}"}

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def _create(client, h, slug="alpha", name="Alpha") -> str:
    r = client.post("/api/v1/projects", headers=h, json={"project_slug": slug, "name": name})
    assert r.status_code == 200, r.text
    return r.json()["project_id"]


def test_get_by_id(env) -> None:
    client, h = env
    pid = _create(client, h)
    r = client.get(f"/api/v1/projects/{pid}", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Alpha"
    assert r.json()["ticket_count"] == 0


def test_patch_edits_fields(env) -> None:
    client, h = env
    pid = _create(client, h)
    assert (
        client.patch(f"/api/v1/projects/{pid}", headers=h, json={"name": "Alpha2"}).status_code
        == 200
    )
    assert client.get(f"/api/v1/projects/{pid}", headers=h).json()["name"] == "Alpha2"


def test_archive_then_restore(env) -> None:
    client, h = env
    pid = _create(client, h)
    assert client.post(f"/api/v1/projects/{pid}/archive", headers=h).json()["active"] is False
    assert client.get(f"/api/v1/projects/{pid}", headers=h).json()["active"] is False
    assert client.post(f"/api/v1/projects/{pid}/restore", headers=h).json()["active"] is True
    assert client.get(f"/api/v1/projects/{pid}", headers=h).json()["active"] is True


def test_hard_delete_by_id(env) -> None:
    client, h = env
    pid = _create(client, h)
    assert client.delete(f"/api/v1/projects/{pid}", headers=h).json()["deleted"] is True
    assert client.get(f"/api/v1/projects/{pid}", headers=h).status_code == 404


def test_delete_by_slug_fallback(env) -> None:
    client, h = env
    _create(client, h, slug="beta", name="Beta")
    # The SPA normally sends _id, but slug must still resolve for back-compat.
    assert client.delete("/api/v1/projects/beta", headers=h).json()["deleted"] is True


def test_routes_404_on_unknown(env) -> None:
    client, h = env
    assert client.get("/api/v1/projects/nonexistent", headers=h).status_code == 404
    assert client.delete("/api/v1/projects/nonexistent", headers=h).status_code == 404


def test_write_requires_scope(env) -> None:
    client, _ = env
    # No auth at all → 401 from require_scope's bearer path.
    assert client.delete("/api/v1/projects/whatever").status_code == 401
