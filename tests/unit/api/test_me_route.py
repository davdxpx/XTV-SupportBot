"""End-to-end tests for ``GET /api/v1/me``."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

_BOT_TOKEN = "123456:test-token"


def _sign(pairs: list[tuple[str, str]]) -> str:
    filtered = sorted((k, v) for k, v in pairs if k != "hash")
    data_check = "\n".join(f"{k}={v}" for k, v in filtered)
    secret = hmac.new(b"WebAppData", _BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode(filtered + [("hash", h)])


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("API_ID", "1")
    monkeypatch.setenv("API_HASH", "x")
    monkeypatch.setenv("BOT_TOKEN", _BOT_TOKEN)
    monkeypatch.setenv("MONGO_URI", "mongodb://x")
    monkeypatch.setenv("ADMIN_CHANNEL_ID", "-100")
    monkeypatch.setenv("ADMIN_IDS", "42")
    monkeypatch.setenv("WEB_ENABLED", "false")

    from xtv_support.config import settings as settings_mod

    saved = settings_mod.settings
    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    from xtv_support.api.server import create_app

    yield TestClient(create_app(db=None))

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def test_me_with_valid_init_data_returns_user(client: TestClient) -> None:
    raw = _sign(
        [
            (
                "user",
                json.dumps({"id": 42, "first_name": "Luca", "language_code": "en"}),
            ),
            ("auth_date", str(int(time.time()))),
        ]
    )
    r = client.get("/api/v1/me", headers={"X-Telegram-Init-Data": raw})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == 42
    assert body["first_name"] == "Luca"
    assert body["is_admin"] is True


def test_me_without_credentials_returns_401(client: TestClient) -> None:
    r = client.get("/api/v1/me")
    assert r.status_code == 401, r.text


def test_me_with_bad_init_data_returns_401(client: TestClient) -> None:
    r = client.get("/api/v1/me", headers={"X-Telegram-Init-Data": "tampered"})
    assert r.status_code == 401, r.text


def test_me_with_bearer_no_db_returns_503(client: TestClient) -> None:
    r = client.get("/api/v1/me", headers={"Authorization": "Bearer xtv_test"})
    assert r.status_code == 503, r.text


def test_me_never_returns_422(client: TestClient) -> None:
    """Regression guard — 422 means FastAPI rejected before our handler ran."""
    for headers in (
        {},
        {"Authorization": "Bearer xtv_invalid"},
        {"Authorization": "Basic foo"},
    ):
        r = client.get("/api/v1/me", headers=headers)
        assert r.status_code != 422, f"422 with headers {headers}: {r.text}"
