"""Phase 5a — web RBAC management (roles + teams) and the grant-rank guard."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import security as sec
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import migrations
from xtv_support.infrastructure.db import roles as roles_repo

_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


@pytest.fixture
def env() -> Iterator[tuple[TestClient, object]]:
    import os

    os.environ["ADMIN_IDS"] = "1"
    os.environ["WEB_ENABLED"] = "false"
    os.environ["SESSION_COOKIE_SECURE"] = "false"

    from xtv_support.config import settings as settings_mod

    saved = settings_mod.settings
    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    db = AsyncMongoMockClient().testdb
    _run(migrations.ensure_indexes(db))

    from xtv_support.api.server import create_app

    app = create_app(db=db)
    yield app, db

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def _owner_headers(db) -> dict:
    key = _run(sec.create_key(db, label="k", scopes=["admin:full"], created_by=1)).plaintext
    return {"Authorization": f"Bearer {key}"}


# ---- roles (owner-equivalent api key) --------------------------------------
def test_roles_grant_list_revoke(env) -> None:
    app, db = env
    c = TestClient(app)
    h = _owner_headers(db)
    assert (
        c.post("/api/v1/rbac/roles", headers=h, json={"user_id": 555, "role": "agent"}).status_code
        == 200
    )
    body = c.get("/api/v1/rbac/roles", headers=h).json()
    assert any(a["user_id"] == 555 and a["role"] == "agent" for a in body["items"])
    assert "owner" in body["roles"]
    assert c.delete("/api/v1/rbac/roles/555", headers=h).status_code == 200
    assert all(a["user_id"] != 555 for a in c.get("/api/v1/rbac/roles", headers=h).json()["items"])


def test_invalid_role_rejected(env) -> None:
    app, db = env
    c = TestClient(app)
    r = c.post(
        "/api/v1/rbac/roles", headers=_owner_headers(db), json={"user_id": 5, "role": "wizard"}
    )
    assert r.status_code == 400


def test_rbac_requires_auth(env) -> None:
    app, _ = env
    assert TestClient(app).get("/api/v1/rbac/roles").status_code == 401


# ---- teams ------------------------------------------------------------------
def test_team_lifecycle(env) -> None:
    app, db = env
    c = TestClient(app)
    h = _owner_headers(db)
    assert (
        c.post(
            "/api/v1/rbac/teams", headers=h, json={"team_id": "tier1", "name": "Tier 1"}
        ).status_code
        == 200
    )
    assert (
        c.post("/api/v1/rbac/teams/tier1/members", headers=h, json={"user_id": 555}).status_code
        == 200
    )
    teams = {t["id"]: t for t in c.get("/api/v1/rbac/teams", headers=h).json()["items"]}
    assert 555 in teams["tier1"]["member_ids"]
    assert c.request("DELETE", "/api/v1/rbac/teams/tier1/members/555", headers=h).status_code == 200
    assert c.delete("/api/v1/rbac/teams/tier1", headers=h).status_code == 200
    assert "tier1" not in {t["id"] for t in c.get("/api/v1/rbac/teams", headers=h).json()["items"]}


def test_invalid_team_slug_rejected(env) -> None:
    app, db = env
    c = TestClient(app)
    r = c.post(
        "/api/v1/rbac/teams", headers=_owner_headers(db), json={"team_id": "Bad Slug!", "name": "X"}
    )
    assert r.status_code == 400


# ---- grant-rank guard (session account that is only ADMIN) ------------------
def _register_admin_session(app, db, tg_id: int, username: str) -> TestClient:
    invite = _run(
        sec.create_key(
            db, label="i", scopes=[], created_by=1, allow_registration=True, target_user_id=tg_id
        )
    ).plaintext
    client = TestClient(app)
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "first_name": "A",
            "password": "longenoughpw",
            "api_key": invite,
        },
    )
    assert r.status_code == 201, r.text
    return client


def test_admin_cannot_grant_above_own_rank(env) -> None:
    app, db = env
    client = _register_admin_session(app, db, tg_id=900, username="adminx")
    _run(roles_repo.grant(db, user_id=900, role=Role.ADMIN, granted_by=1))
    # ADMIN may grant AGENT…
    assert (
        client.post("/api/v1/rbac/roles", json={"user_id": 42, "role": "agent"}).status_code == 200
    )
    # …but NOT OWNER (above their own rank).
    r = client.post("/api/v1/rbac/roles", json={"user_id": 42, "role": "owner"})
    assert r.status_code == 403
