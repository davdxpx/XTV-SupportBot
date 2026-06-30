"""Ticket attachments — owner upload + owner serve, with guards.

The real service uploads via the bot (pyrogram); here we stub the service
module and the bot-client resolver so the route logic (ownership, size cap,
history wiring, streaming) is exercised without Telegram.
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

from xtv_support.infrastructure.db import migrations
from xtv_support.infrastructure.db import tickets as tickets_repo

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
def env(monkeypatch) -> Iterator[tuple[TestClient, str]]:
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
    tid = str(_run(tickets_repo.create(db, project_id=None, user_id=555, message="hi")))

    # Stub the ticket service (real one imports pyrogram) + the client resolver.
    stub = types.ModuleType("xtv_support.services.tickets.service")

    async def attach_to_ticket(
        _client, dbx, *, ticket, data, filename, content_type, sender="user", caption=""
    ):
        media_type = "photo" if (content_type or "").startswith("image/") else "document"
        await tickets_repo.append_history(
            dbx,
            ticket["_id"],
            sender=sender,
            text=caption or f"({media_type})",
            message_type=media_type,
            file_id="fid123",
        )
        return media_type, "fid123"

    async def download_attachment(_client, ticket, index):
        history = ticket.get("history") or []
        if index < 0 or index >= len(history) or not history[index].get("file_id"):
            return None
        return b"IMGDATA", "image/jpeg"

    stub.attach_to_ticket = attach_to_ticket
    stub.download_attachment = download_attachment
    monkeypatch.setitem(sys.modules, "xtv_support.services.tickets.service", stub)

    from xtv_support.api.routes import me as me_routes

    monkeypatch.setattr(me_routes, "_resolve_bot_client", lambda request: object())

    from xtv_support.api.server import create_app

    client = TestClient(create_app(db=db))
    yield client, tid

    settings_mod.settings = saved
    settings_mod.get_settings.cache_clear()


def test_upload_and_serve_roundtrip(env) -> None:
    client, tid = env
    h = {"X-Telegram-Init-Data": _init_data(555)}
    r = client.post(
        f"/api/v1/me/tickets/{tid}/attach", headers=h, files={"file": ("p.png", b"x", "image/png")}
    )
    assert r.status_code == 201, r.text
    assert r.json()["type"] == "photo"

    # The detail view now exposes an attachment index on the new history entry.
    detail = client.get(f"/api/v1/me/tickets/{tid}", headers=h).json()
    idx = next(e["attachment_index"] for e in detail["history"] if "attachment_index" in e)
    served = client.get(f"/api/v1/me/tickets/{tid}/attachments/{idx}", headers=h)
    assert served.status_code == 200
    assert served.content == b"IMGDATA"
    assert served.headers["content-type"].startswith("image/")


def test_upload_rejects_other_users_ticket(env) -> None:
    client, tid = env
    r = client.post(
        f"/api/v1/me/tickets/{tid}/attach",
        headers={"X-Telegram-Init-Data": _init_data(999)},
        files={"file": ("p.png", b"x", "image/png")},
    )
    assert r.status_code == 404


def test_upload_size_cap(env, monkeypatch) -> None:
    client, tid = env
    from xtv_support.api.routes import me as me_routes

    monkeypatch.setattr(me_routes, "_MAX_ATTACHMENT_BYTES", 4)
    r = client.post(
        f"/api/v1/me/tickets/{tid}/attach",
        headers={"X-Telegram-Init-Data": _init_data(555)},
        files={"file": ("big.bin", b"0123456789", "application/octet-stream")},
    )
    assert r.status_code == 413


def test_serve_unknown_index_404(env) -> None:
    client, tid = env
    r = client.get(
        f"/api/v1/me/tickets/{tid}/attachments/99",
        headers={"X-Telegram-Init-Data": _init_data(555)},
    )
    assert r.status_code == 404
