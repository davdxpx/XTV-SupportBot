"""Phase 5c — web management for macros & KB articles."""

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


def test_macro_crud(env) -> None:
    c, h = env
    mid = c.post("/api/v1/macros", headers=h, json={"name": "greet", "body": "Hi"}).json()["macro"][
        "id"
    ]
    assert (
        c.post("/api/v1/macros", headers=h, json={"name": "greet", "body": "x"}).status_code == 409
    )
    assert c.patch(f"/api/v1/macros/{mid}", headers=h, json={"body": "Hello"}).status_code == 200
    assert any(m["id"] == mid for m in c.get("/api/v1/macros", headers=h).json()["items"])
    assert c.delete(f"/api/v1/macros/{mid}", headers=h).status_code == 200


def test_macro_validation(env) -> None:
    c, h = env
    assert c.post("/api/v1/macros", headers=h, json={"name": "", "body": "x"}).status_code == 400


def test_kb_crud(env) -> None:
    c, h = env
    assert (
        c.post(
            "/api/v1/kb", headers=h, json={"slug": "reset", "title": "Reset", "body": "steps"}
        ).status_code
        == 201
    )
    assert (
        c.post(
            "/api/v1/kb", headers=h, json={"slug": "reset", "title": "x", "body": "y"}
        ).status_code
        == 409
    )
    assert c.patch("/api/v1/kb/reset", headers=h, json={"title": "Reset PW"}).status_code == 200
    assert c.patch("/api/v1/kb/missing", headers=h, json={"title": "x"}).status_code == 404
    assert any(a["slug"] == "reset" for a in c.get("/api/v1/kb", headers=h).json()["items"])
    assert c.delete("/api/v1/kb/reset", headers=h).status_code == 200


def test_content_requires_auth(env) -> None:
    c, _ = env
    assert c.get("/api/v1/macros").status_code == 401
    assert c.get("/api/v1/kb").status_code == 401
