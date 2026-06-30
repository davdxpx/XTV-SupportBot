"""Phase 4 — supported-languages endpoint (incl. German) + ticket rate limit."""

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

from xtv_support.infrastructure.db import migrations
from xtv_support.services.cooldown.service import CooldownService

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
    return urlencode(pairs + [("hash", hmac.new(secret, dc.encode(), hashlib.sha256).hexdigest())])


class _FakeContainer:
    def __init__(self, cooldown: CooldownService) -> None:
        self._cd = cooldown

    def resolve(self, cls):
        if cls is CooldownService:
            return self._cd
        raise KeyError(cls)  # e.g. the bot Client → caller degrades


@pytest.fixture
def make_app() -> Iterator:
    import os

    os.environ["BOT_TOKEN"] = _BOT_TOKEN
    os.environ["ADMIN_IDS"] = "1"
    os.environ["ADMIN_CHANNEL_ID"] = "-100123"
    os.environ["WEB_ENABLED"] = "false"

    from xtv_support.config import settings as settings_mod

    saved = settings_mod.settings
    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    from xtv_support.api.server import create_app

    def _build(cooldown: CooldownService | None) -> TestClient:
        db = AsyncMongoMockClient().testdb
        _run(migrations.ensure_indexes(db))
        app = create_app(db=db)
        if cooldown is not None:
            app.state.container = _FakeContainer(cooldown)
        return TestClient(app)

    yield _build

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def test_languages_endpoint_includes_german(make_app) -> None:
    client = make_app(None)
    r = client.get("/api/v1/me/languages")
    assert r.status_code == 200
    items = {i["code"]: i for i in r.json()["items"]}
    assert "de" in items and items["de"]["name"] == "Deutsch"
    assert "en" in items


def test_ticket_creation_rate_limited(make_app) -> None:
    # rate=0 → the limiter denies the very first attempt.
    client = make_app(CooldownService(rate=0, window=60, mute_seconds=30))
    r = client.post(
        "/api/v1/me/tickets",
        headers={"X-Telegram-Init-Data": _init_data(555)},
        json={"message": "spam"},
    )
    assert r.status_code == 429
    assert r.json()["detail"]["error"] == "cooldown"


def test_ticket_creation_allowed_under_limit(make_app) -> None:
    # Generous limit → creation proceeds (falls back to a bare insert with no bot client).
    client = make_app(CooldownService(rate=100, window=60, mute_seconds=30))
    r = client.post(
        "/api/v1/me/tickets",
        headers={"X-Telegram-Init-Data": _init_data(555)},
        json={"message": "legit question"},
    )
    assert r.status_code == 201, r.text
