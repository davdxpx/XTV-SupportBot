"""redeem_for_registration — single-use, atomic, burns the key."""

from __future__ import annotations

import asyncio

import pytest
from mongomock_motor import AsyncMongoMockClient

from xtv_support.api import security as sec


@pytest.fixture
def db():
    return AsyncMongoMockClient().testdb


async def _mint(db, **over):
    kw = dict(label="invite", scopes=[], created_by=1, allow_registration=True, target_user_id=555)
    kw.update(over)
    return await sec.create_key(db, **kw)


async def test_create_requires_target_for_registration(db) -> None:
    with pytest.raises(ValueError):
        await sec.create_key(
            db, label="x", scopes=[], created_by=1, allow_registration=True, target_user_id=None
        )


async def test_redeem_succeeds_once_then_fails(db) -> None:
    pt = (await _mint(db)).plaintext
    first = await sec.redeem_for_registration(db, pt)
    assert first is not None
    assert first.target_user_id == 555
    assert await sec.redeem_for_registration(db, pt) is None


async def test_redeem_burns_key_for_bearer_too(db) -> None:
    pt = (await _mint(db)).plaintext
    await sec.redeem_for_registration(db, pt)
    # The burned key is dead as a bearer credential as well.
    assert await sec.lookup_by_key(db, pt) is None


async def test_redeem_rejects_non_registration_key(db) -> None:
    new = await sec.create_key(db, label="bearer", scopes=["admin:full"], created_by=1)
    assert await sec.redeem_for_registration(db, new.plaintext) is None


async def test_redeem_rejects_revoked_key(db) -> None:
    new = await _mint(db)
    await sec.revoke_key(db, new.meta.key_id)
    assert await sec.redeem_for_registration(db, new.plaintext) is None


async def test_redeem_rejects_bad_format(db) -> None:
    assert await sec.redeem_for_registration(db, "not-an-xtv-key") is None


async def test_concurrent_redemption_exactly_one_wins(db) -> None:
    pt = (await _mint(db)).plaintext
    results = await asyncio.gather(
        sec.redeem_for_registration(db, pt),
        sec.redeem_for_registration(db, pt),
        sec.redeem_for_registration(db, pt),
    )
    winners = [r for r in results if r is not None]
    assert len(winners) == 1
