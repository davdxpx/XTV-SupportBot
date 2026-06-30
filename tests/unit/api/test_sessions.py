"""Server-side session lifecycle, expiry, and revocation."""

from __future__ import annotations

from datetime import timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import sessions
from xtv_support.infrastructure.db import admin_accounts as repo
from xtv_support.utils.time import utcnow


@pytest.fixture
async def setup():
    db = AsyncMongoMockClient().testdb
    acc = await repo.create(
        db,
        username="u",
        display_username="u",
        first_name="U",
        last_name=None,
        password_hash="h",
        telegram_user_id=555,
        created_via_key_id="k",
    )
    return db, acc


async def test_create_and_resolve(setup) -> None:
    db, acc = setup
    raw = await sessions.create_session(db, acc.id)
    resolved = await sessions.resolve_session(db, raw)
    assert resolved is not None and resolved.id == acc.id


async def test_raw_id_is_not_stored_plaintext(setup) -> None:
    db, acc = setup
    raw = await sessions.create_session(db, acc.id)
    doc = await db.sessions.find_one({"account_id": acc.id})
    assert doc["session_hash"] != raw


async def test_expired_session_resolves_none(setup) -> None:
    db, acc = setup
    raw = await sessions.create_session(db, acc.id)
    await db.sessions.update_one(
        {"account_id": acc.id}, {"$set": {"expires_at": utcnow() - timedelta(seconds=1)}}
    )
    assert await sessions.resolve_session(db, raw) is None


async def test_revoke_session(setup) -> None:
    db, acc = setup
    raw = await sessions.create_session(db, acc.id)
    await sessions.revoke_session(db, raw)
    assert await sessions.resolve_session(db, raw) is None


async def test_disabled_account_kills_live_session(setup) -> None:
    db, acc = setup
    raw = await sessions.create_session(db, acc.id)
    assert await sessions.resolve_session(db, raw) is not None
    await repo.set_disabled(db, acc.id, disabled=True)
    # Existing session must stop resolving immediately, not at expiry.
    assert await sessions.resolve_session(db, raw) is None


async def test_revoke_all_sessions_for(setup) -> None:
    db, acc = setup
    r1 = await sessions.create_session(db, acc.id)
    r2 = await sessions.create_session(db, acc.id)
    await sessions.revoke_all_sessions_for(db, acc.id)
    assert await sessions.resolve_session(db, r1) is None
    assert await sessions.resolve_session(db, r2) is None
