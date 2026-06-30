"""Web ticket creation goes through the shared service, and live stats.

Guards the Phase-1 fix: the Mini-App POST /me/tickets must create the ticket
via the same service the bot uses (so a forum topic is produced), and must
degrade to a bare insert (still visible in the console) when no bot Client is
available. The admin console stats read live data, never the empty rollup.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import sys
import time
import types
from collections.abc import Iterator
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import security as sec
from xtv_support.infrastructure.db import migrations

_BOT_TOKEN = "123456:test-token"
_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


def _init_data(uid: int) -> str:
    pairs = sorted(
        [("user", json.dumps({"id": uid, "first_name": "U"})), ("auth_date", str(int(time.time())))]
    )
    dc = "\n".join(f"{k}={v}" for k, v in pairs)
    secret = hmac.new(b"WebAppData", _BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dc.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs + [("hash", h)])


@pytest.fixture
def env() -> Iterator[tuple[TestClient, object]]:
    import os

    os.environ["BOT_TOKEN"] = _BOT_TOKEN
    os.environ["ADMIN_IDS"] = "1"
    os.environ["ADMIN_CHANNEL_ID"] = "-100123"
    os.environ["WEB_ENABLED"] = "false"

    from xtv_support.config import settings as settings_mod

    saved = settings_mod.settings
    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    db = AsyncMongoMockClient().testdb
    _run(migrations.ensure_indexes(db))

    from xtv_support.api.server import create_app

    client = TestClient(create_app(db=db))
    yield client, db

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def _admin_key(db) -> str:
    return _run(sec.create_key(db, label="k", scopes=["admin:full"], created_by=1)).plaintext


def test_web_ticket_fallback_when_no_client(env) -> None:
    # No container/Client (pyrogram absent) → degrade to a bare insert that is
    # still persisted and visible in the console.
    client, db = env
    r = client.post(
        "/api/v1/me/tickets",
        headers={"X-Telegram-Init-Data": _init_data(555)},
        json={"message": "hello"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "open"
    stats = client.get(
        "/api/v1/tickets/stats", headers={"Authorization": f"Bearer {_admin_key(db)}"}
    )
    assert stats.json()["total"] == 1
    assert stats.json()["open"] == 1


def test_web_ticket_delegates_to_shared_service(env, monkeypatch) -> None:
    # When a bot Client is available, creation must go through the unified
    # ticket service (which creates the forum topic) — not a bare insert.
    client, db = env

    calls: list[dict] = []

    stub = types.ModuleType("xtv_support.services.tickets.service")

    async def create_ticket(_client, dbx, **kw):  # noqa: ANN001
        calls.append(kw)
        from xtv_support.infrastructure.db import tickets as tr

        tid = await tr.create(dbx, project_id=None, user_id=kw["user_id"], message=kw["text"])
        return await tr.get(dbx, tid)

    stub.create_ticket = create_ticket
    monkeypatch.setitem(sys.modules, "xtv_support.services.tickets.service", stub)

    from xtv_support.api.routes import me as me_routes

    monkeypatch.setattr(me_routes, "_resolve_bot_client", lambda request: object())

    r = client.post(
        "/api/v1/me/tickets",
        headers={"X-Telegram-Init-Data": _init_data(777)},
        json={"message": "via service"},
    )
    assert r.status_code == 201, r.text
    assert len(calls) == 1
    assert calls[0]["user_id"] == 777
    assert calls[0]["text"] == "via service"


def test_stats_endpoint_requires_scope(env) -> None:
    client, _ = env
    assert client.get("/api/v1/tickets/stats").status_code == 401
