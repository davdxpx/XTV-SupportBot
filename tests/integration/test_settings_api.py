"""Phase D1 — /api/v1/settings (runtime operational settings)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import security as sec
from xtv_support.config import runtime
from xtv_support.infrastructure.db import migrations

_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


@pytest.fixture
def env() -> Iterator[tuple[TestClient, dict, object]]:
    import os

    os.environ["ADMIN_IDS"] = "1"
    os.environ["WEB_ENABLED"] = "false"

    from xtv_support.config import settings as settings_mod

    saved = settings_mod.settings
    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    runtime.invalidate()
    db = AsyncMongoMockClient().testdb
    _run(migrations.ensure_indexes(db))
    key = _run(sec.create_key(db, label="k", scopes=["admin:full"], created_by=1)).plaintext

    from xtv_support.api.server import create_app

    client = TestClient(create_app(db=db))
    yield client, {"Authorization": f"Bearer {key}"}, db

    runtime.invalidate()
    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def test_get_returns_schema_with_defaults(env) -> None:
    client, h, _ = env
    body = client.get("/api/v1/settings", headers=h).json()
    keys = {i["key"] for i in body["items"]}
    assert "SLA_WARN_MINUTES" in keys
    assert "TOPIC_DELETE_AFTER_CLOSE_MINUTES" in keys
    # no secrets leak into the settings surface
    assert "BOT_TOKEN" not in keys
    assert "MONGO_URI" not in keys


def test_patch_persists_and_reflects(env) -> None:
    client, h, _ = env
    r = client.patch("/api/v1/settings", headers=h, json={"AUTO_CLOSE_DAYS": 3})
    assert r.status_code == 200, r.text
    item = next(i for i in r.json()["items"] if i["key"] == "AUTO_CLOSE_DAYS")
    assert item["value"] == 3
    assert item["overridden"] is True
    # persisted across a fresh GET
    again = client.get("/api/v1/settings", headers=h).json()
    assert next(i for i in again["items"] if i["key"] == "AUTO_CLOSE_DAYS")["value"] == 3


def test_patch_rejects_unknown_key(env) -> None:
    client, h, _ = env
    assert client.patch("/api/v1/settings", headers=h, json={"BOT_TOKEN": "x"}).status_code == 400


def test_patch_rejects_out_of_range(env) -> None:
    client, h, _ = env
    assert (
        client.patch("/api/v1/settings", headers=h, json={"AUTO_CLOSE_DAYS": 0}).status_code == 400
    )


def test_patch_rejects_bad_choice(env) -> None:
    client, h, _ = env
    assert client.patch("/api/v1/settings", headers=h, json={"UI_MODE": "nope"}).status_code == 400


def test_requires_auth(env) -> None:
    client, _, _ = env
    assert client.get("/api/v1/settings").status_code == 401
