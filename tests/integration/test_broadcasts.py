"""Phase 5d — web broadcast management (list / compose+start / cancel).

The real BroadcastManager needs pyrogram; here we stub the service module and
inject a fake manager into the container so the route logic is exercised
without Telegram.
"""

from __future__ import annotations

import asyncio
import sys
import types
from collections.abc import Iterator

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import security as sec
from xtv_support.infrastructure.db import migrations

_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


class _FakeManager:
    def __init__(self) -> None:
        self.busy = False
        self.started: list[str] = []
        self.cancelled = False

    async def start_from_web(self, *, text: str):
        if self.busy:
            return None
        self.started.append(text)
        return ObjectId()

    async def cancel(self) -> None:
        self.cancelled = True


@pytest.fixture
def env(monkeypatch) -> Iterator[tuple[TestClient, dict, _FakeManager, object]]:
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

    # Stub the broadcast service module (real one imports pyrogram).
    stub = types.ModuleType("xtv_support.services.broadcasts.service")

    class BroadcastManager:  # resolve key
        pass

    stub.BroadcastManager = BroadcastManager
    monkeypatch.setitem(sys.modules, "xtv_support.services.broadcasts.service", stub)

    fake = _FakeManager()

    class FakeContainer:
        def resolve(self, cls):
            if cls is BroadcastManager:
                return fake
            raise KeyError(cls)

    from xtv_support.api.server import create_app

    app = create_app(db=db)
    app.state.container = FakeContainer()
    client = TestClient(app)
    yield client, {"Authorization": f"Bearer {key}"}, fake, db

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def test_create_delegates_to_manager(env) -> None:
    client, h, fake, _ = env
    r = client.post("/api/v1/broadcasts", headers=h, json={"text": "hello all"})
    assert r.status_code == 201, r.text
    assert fake.started == ["hello all"]


def test_empty_text_rejected(env) -> None:
    client, h, _, _ = env
    assert client.post("/api/v1/broadcasts", headers=h, json={"text": "  "}).status_code == 400


def test_create_conflict_when_running(env) -> None:
    client, h, fake, _ = env
    fake.busy = True
    assert client.post("/api/v1/broadcasts", headers=h, json={"text": "x"}).status_code == 409


def test_cancel(env) -> None:
    client, h, fake, _ = env
    assert client.post("/api/v1/broadcasts/cancel", headers=h).status_code == 200
    assert fake.cancelled is True


def test_list_reports_active(env) -> None:
    client, h, _, db = env
    _run(db.broadcasts.insert_one({"text": "t", "state": "running", "total": 5, "sent": 2}))
    body = client.get("/api/v1/broadcasts", headers=h).json()
    assert body["active"] is True
    assert body["count"] == 1


def test_requires_auth(env) -> None:
    client, _, _, _ = env
    assert client.get("/api/v1/broadcasts").status_code == 401
