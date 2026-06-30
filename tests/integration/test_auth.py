"""Integration tests for the admin-account auth flow.

Covers registration (happy path + every rejection code), login (generic
error on unknown/wrong-pw/disabled), the target_user_id RBAC binding,
current_principal precedence, account management, and the /me is_admin
fix for legacy API keys.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import ratelimit
from xtv_support.api import security as sec
from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import migrations
from xtv_support.infrastructure.db import roles as roles_repo

_BOT_TOKEN = "123456:test-token"


_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


def _sign_init_data(user: dict) -> str:
    pairs = sorted([("user", json.dumps(user)), ("auth_date", str(int(time.time())))])
    data_check = "\n".join(f"{k}={v}" for k, v in pairs)
    secret = hmac.new(b"WebAppData", _BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs + [("hash", h)])


@pytest.fixture
def env() -> Iterator[tuple[TestClient, object]]:
    import os

    os.environ["BOT_TOKEN"] = _BOT_TOKEN
    os.environ["ADMIN_IDS"] = "1"
    os.environ["WEB_ENABLED"] = "false"
    os.environ["SESSION_COOKIE_SECURE"] = "false"

    from xtv_support.config import settings as settings_mod

    saved = settings_mod.settings
    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    ratelimit.reset()
    db = AsyncMongoMockClient().testdb
    _run(migrations.ensure_indexes(db))

    from xtv_support.api.server import create_app

    client = TestClient(create_app(db=db))
    yield client, db

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def _invite(db, target: int, by: int = 1) -> str:
    return _run(
        sec.create_key(
            db,
            label="invite",
            scopes=[],
            created_by=by,
            allow_registration=True,
            target_user_id=target,
        )
    ).plaintext


def _register(client, key, *, username="davidk", first="David", last=None, password="longenoughpw"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "first_name": first,
            "last_name": last,
            "password": password,
            "api_key": key,
        },
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def test_register_happy_path_sets_session(env) -> None:
    client, db = env
    r = _register(client, _invite(db, 555))
    assert r.status_code == 201, r.text
    assert r.json()["account"]["display_username"] == "davidk"
    assert "xtv_admin_session" in r.cookies
    # logged in immediately
    assert client.get("/api/v1/me").status_code == 200


def test_register_invalid_key_format(env) -> None:
    client, _ = env
    r = _register(client, "totally-wrong")
    assert r.status_code == 400 and r.json()["detail"] == "invalid_api_key_format"


def test_register_used_key_is_vague_403(env) -> None:
    client, db = env
    key = _invite(db, 555)
    assert _register(client, key).status_code == 201
    r = _register(TestClient(client.app), key, username="other")
    assert r.status_code == 403 and r.json()["detail"] == "invalid_or_used_registration_key"


def test_register_invalid_username(env) -> None:
    client, db = env
    r = _register(client, _invite(db, 555), username="1bad")
    assert r.status_code == 400 and r.json()["detail"] == "invalid_username_format"


def test_register_username_taken(env) -> None:
    client, db = env
    assert _register(client, _invite(db, 555), username="taken").status_code == 201
    r = _register(TestClient(client.app), _invite(db, 556), username="TAKEN")
    assert r.status_code == 409 and r.json()["detail"] == "username_taken"


def test_register_empty_first_name(env) -> None:
    client, db = env
    r = _register(client, _invite(db, 555), first="   ")
    assert r.status_code == 400 and r.json()["detail"] == "invalid_first_name"


def test_register_weak_password_too_short(env) -> None:
    client, db = env
    r = _register(client, _invite(db, 555), password="short")
    assert r.status_code == 400 and r.json()["detail"] == "weak_password"


def test_register_weak_password_equals_username(env) -> None:
    client, db = env
    r = _register(client, _invite(db, 555), username="samesame", password="SameSame")
    assert r.status_code == 400 and r.json()["detail"] == "weak_password"


# ---------------------------------------------------------------------------
# target_user_id RBAC binding — THE crux
# ---------------------------------------------------------------------------
def test_account_binds_to_target_not_creator(env) -> None:
    client, db = env
    # key created BY admin A=1 but targeted AT user B=555
    _register(client, _invite(db, target=555, by=1))
    # B (555) is AGENT; A (1) is ADMIN via ADMIN_IDS. Account must follow B.
    _run(roles_repo.grant(db, user_id=555, role=Role.AGENT, granted_by=1))
    me = client.get("/api/v1/me").json()
    assert me["id"] == 555
    assert me["role"] == "agent"
    assert me["is_admin"] is True  # AGENT can open the console


def test_no_role_doc_is_user_not_admin(env) -> None:
    client, db = env
    _register(client, _invite(db, 555))
    me = client.get("/api/v1/me").json()
    assert me["role"] == "user" and me["is_admin"] is False


# ---------------------------------------------------------------------------
# Login — generic error, no enumeration
# ---------------------------------------------------------------------------
def test_login_generic_errors_are_identical(env) -> None:
    client, db = env
    _register(client, _invite(db, 555), username="real", password="longenoughpw")
    fresh = TestClient(client.app)
    wrong = fresh.post("/api/v1/auth/login", json={"username": "real", "password": "nope"})
    unknown = fresh.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "longenoughpw"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "invalid_credentials"


def test_login_disabled_account_same_generic_error(env) -> None:
    client, db = env
    acc_id = _register(client, _invite(db, 555), username="real").json()["account"]["id"]
    from xtv_support.infrastructure.db import admin_accounts as accounts_repo

    _run(accounts_repo.set_disabled(db, acc_id, disabled=True))
    r = TestClient(client.app).post(
        "/api/v1/auth/login", json={"username": "real", "password": "longenoughpw"}
    )
    assert r.status_code == 401 and r.json()["detail"] == "invalid_credentials"


def test_login_happy_then_logout(env) -> None:
    client, db = env
    _register(client, _invite(db, 555), username="real")
    c = TestClient(client.app)
    assert (
        c.post(
            "/api/v1/auth/login", json={"username": "real", "password": "longenoughpw"}
        ).status_code
        == 200
    )
    assert c.get("/api/v1/me").status_code == 200
    assert c.post("/api/v1/auth/logout").status_code == 200
    assert c.get("/api/v1/me").status_code == 401


# ---------------------------------------------------------------------------
# current_principal precedence: initData > session > bearer
# ---------------------------------------------------------------------------
def test_precedence_initdata_beats_session(env) -> None:
    client, db = env
    _register(client, _invite(db, 555))  # client now holds a session cookie
    init = _sign_init_data({"id": 999, "first_name": "Tg"})
    me = client.get("/api/v1/me", headers={"X-Telegram-Init-Data": init}).json()
    assert me["id"] == 999  # telegram identity wins over the cookie's 555


def test_precedence_session_beats_bearer(env) -> None:
    client, db = env
    _register(client, _invite(db, 555))  # session cookie for tg 555 (role USER)
    bearer = _run(sec.create_key(db, label="k", scopes=["admin:full"], created_by=7)).plaintext
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {bearer}"}).json()
    assert me["id"] == 555 and me["is_admin"] is False  # session wins, not the admin key


# ---------------------------------------------------------------------------
# /me is_admin fix for legacy API keys
# ---------------------------------------------------------------------------
def test_me_apikey_admin_full_is_admin_true(env) -> None:
    client, db = env
    key = _run(sec.create_key(db, label="k", scopes=["admin:full"], created_by=7)).plaintext
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {key}"}).json()
    assert me["is_admin"] is True


def test_me_apikey_readonly_is_admin_false(env) -> None:
    client, db = env
    key = _run(sec.create_key(db, label="k", scopes=["tickets:read"], created_by=7)).plaintext
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {key}"}).json()
    assert me["is_admin"] is False  # the bug is fixed


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------
def test_change_password_happy_then_relogin(env) -> None:
    client, db = env
    _register(client, _invite(db, 555), username="real", password="longenoughpw")
    r = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "longenoughpw", "new_password": "brandnewpw123"},
    )
    assert r.status_code == 200, r.text
    # caller stays logged in on this device (re-issued cookie)
    assert client.get("/api/v1/me").status_code == 200
    # old password no longer works, new one does
    fresh = TestClient(client.app)
    assert (
        fresh.post(
            "/api/v1/auth/login", json={"username": "real", "password": "longenoughpw"}
        ).status_code
        == 401
    )
    assert (
        fresh.post(
            "/api/v1/auth/login", json={"username": "real", "password": "brandnewpw123"}
        ).status_code
        == 200
    )


def test_change_password_wrong_current_is_403(env) -> None:
    client, db = env
    _register(client, _invite(db, 555), username="real", password="longenoughpw")
    r = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongpw", "new_password": "brandnewpw123"},
    )
    assert r.status_code == 403


def test_change_password_weak_new_is_400(env) -> None:
    client, db = env
    _register(client, _invite(db, 555), username="real", password="longenoughpw")
    r = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "longenoughpw", "new_password": "short"},
    )
    assert r.status_code == 400


def test_change_password_revokes_other_sessions(env) -> None:
    client, db = env
    _register(client, _invite(db, 555), username="real", password="longenoughpw")
    other = TestClient(client.app)
    assert (
        other.post(
            "/api/v1/auth/login", json={"username": "real", "password": "longenoughpw"}
        ).status_code
        == 200
    )
    assert other.get("/api/v1/me").status_code == 200
    # change from the first client -> the second device's session dies
    assert (
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "longenoughpw", "new_password": "brandnewpw123"},
        ).status_code
        == 200
    )
    assert other.get("/api/v1/me").status_code == 401


def test_change_password_requires_account_not_apikey(env) -> None:
    client, db = env
    key = _run(sec.create_key(db, label="k", scopes=["admin:full"], created_by=7)).plaintext
    r = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {key}"},
        json={"current_password": "x", "new_password": "brandnewpw123"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Account management (owner/admin only)
# ---------------------------------------------------------------------------
def test_accounts_disable_kills_session_and_gates_by_role(env) -> None:
    client, db = env
    # admin caller = tg 1 (ADMIN via ADMIN_IDS)
    _register(client, _invite(db, target=1), username="boss")
    # second account: agent tg 555
    agent = TestClient(client.app)
    _register(agent, _invite(db, target=555), username="agent1")
    _run(roles_repo.grant(db, user_id=555, role=Role.AGENT, granted_by=1))

    listing = client.get("/api/v1/auth/accounts")
    assert listing.status_code == 200
    agent_id = next(a["id"] for a in listing.json()["items"] if a["username"] == "agent1")

    # agent (not admin) cannot manage accounts
    assert agent.get("/api/v1/auth/accounts").status_code == 403

    # disable agent -> its live session dies immediately
    assert client.post(f"/api/v1/auth/accounts/{agent_id}/disable").status_code == 200
    assert agent.get("/api/v1/me").status_code == 401
