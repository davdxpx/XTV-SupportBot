"""Phase 5b — web API-key management (list / mint / revoke + invites)."""

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
    key = _run(sec.create_key(db, label="boot", scopes=["admin:full"], created_by=1)).plaintext

    from xtv_support.api.server import create_app

    client = TestClient(create_app(db=db))
    yield client, {"Authorization": f"Bearer {key}"}

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def test_create_lists_and_revoke(env) -> None:
    client, h = env
    r = client.post("/api/v1/apikeys", headers=h, json={"label": "svc", "scopes": ["tickets:read"]})
    assert r.status_code == 201, r.text
    assert r.json()["plaintext"].startswith("xtv_")
    kid = r.json()["key"]["key_id"]
    listing = client.get("/api/v1/apikeys", headers=h).json()
    assert any(k["key_id"] == kid for k in listing["items"])
    assert "admin:full" in listing["scopes"]
    assert client.delete(f"/api/v1/apikeys/{kid}", headers=h).status_code == 200


def test_unknown_scope_rejected(env) -> None:
    client, h = env
    assert (
        client.post(
            "/api/v1/apikeys", headers=h, json={"label": "x", "scopes": ["nope"]}
        ).status_code
        == 400
    )


def test_invite_requires_target(env) -> None:
    client, h = env
    assert (
        client.post(
            "/api/v1/apikeys", headers=h, json={"label": "i", "allow_registration": True}
        ).status_code
        == 400
    )


def test_invite_creates_registration_key(env) -> None:
    client, h = env
    r = client.post(
        "/api/v1/apikeys",
        headers=h,
        json={"label": "i", "allow_registration": True, "target_user_id": 555},
    )
    assert r.status_code == 201
    key = r.json()["key"]
    assert key["registration_capable"] is True
    assert key["target_user_id"] == 555
    assert key["scopes"] == []  # invites carry no bearer power


def test_requires_auth(env) -> None:
    client, _ = env
    assert client.get("/api/v1/apikeys").status_code == 401
    assert (
        client.post("/api/v1/apikeys", json={"label": "x", "scopes": ["tickets:read"]}).status_code
        == 401
    )
