"""GDPR soft-delete + purge tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from xtv_support.services.gdpr.deleter import (
    DEFAULT_GRACE_DAYS,
    cancel_deletion,
    purge_expired,
    request_deletion,
)


class _UsersColl:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.update_one = AsyncMock()
        self.delete_one = AsyncMock()
        self.delete_many = AsyncMock()

    def find(self, query=None, projection=None):
        docs = list(self.docs)
        if query and "deleted_at" in query:
            cutoff = query["deleted_at"].get("$lte")
            docs = [d for d in docs if d.get("deleted_at") and d["deleted_at"] <= cutoff]
        return _AsyncCursor(docs)


class _SimpleColl:
    def __init__(self):
        self.delete_many = AsyncMock()
        self.delete_one = AsyncMock()


class _AsyncCursor:
    def __init__(self, docs):
        self._it = iter(docs)

    def __aiter__(self): return self
    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


async def test_request_deletion_sets_timestamps_and_blocks() -> None:
    db = SimpleNamespace(users=_UsersColl())
    receipt = await request_deletion(db, user_id=7, grace_days=10)
    assert receipt.user_id == 7
    # Delta roughly matches grace window.
    assert (receipt.purge_at - receipt.requested_at).days in {9, 10}
    call = db.users.update_one.await_args.args
    assert call[0] == {"user_id": 7}
    assert call[1]["$set"]["blocked"] is True
    assert "deleted_at" in call[1]["$set"]


async def test_cancel_deletion_reports_result() -> None:
    db = SimpleNamespace(users=_UsersColl())
    db.users.update_one.return_value = MagicMock(modified_count=1)
    assert await cancel_deletion(db, user_id=7) is True

    db.users.update_one.return_value = MagicMock(modified_count=0)
    assert await cancel_deletion(db, user_id=99) is False


async def test_default_grace_constant_is_reasonable() -> None:
    # 30 days is the default per GDPR guidance; locking this prevents
    # accidental drops to 0 that would immediately delete users.
    assert DEFAULT_GRACE_DAYS == 30


async def test_purge_expired_deletes_matching_users() -> None:
    now = datetime.now(timezone.utc)
    db = SimpleNamespace(
        users=_UsersColl([
            {"user_id": 1, "deleted_at": now - timedelta(days=60)},
            {"user_id": 2, "deleted_at": now - timedelta(days=45)},
            {"user_id": 3, "deleted_at": now - timedelta(days=1)},
        ]),
        tickets=_SimpleColl(),
        csat_responses=_SimpleColl(),
        audit_log=_SimpleColl(),
    )

    count = await purge_expired(db, older_than_days=30)
    assert count == 2
    # Check tickets + csat + audit_log hit for each purged user.
    assert db.tickets.delete_many.await_count == 2
    assert db.csat_responses.delete_many.await_count == 2
    assert db.audit_log.delete_many.await_count == 2


async def test_purge_expired_with_no_candidates_is_zero() -> None:
    now = datetime.now(timezone.utc)
    db = SimpleNamespace(
        users=_UsersColl([
            {"user_id": 1, "deleted_at": now - timedelta(days=1)},
        ]),
        tickets=_SimpleColl(),
        csat_responses=_SimpleColl(),
        audit_log=_SimpleColl(),
    )
    count = await purge_expired(db, older_than_days=30)
    assert count == 0
