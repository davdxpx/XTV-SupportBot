"""Live ticket count helper used by the admin console."""

from __future__ import annotations

import pytest
from mongomock_motor import AsyncMongoMockClient

from xtv_support.infrastructure.db import tickets as repo
from xtv_support.utils.time import utcnow


@pytest.fixture
def db():
    return AsyncMongoMockClient().testdb


async def _insert(db, *, status="open", assignee_id=None, created_at=None):
    await db.tickets.insert_one(
        {
            "status": status,
            "assignee_id": assignee_id,
            "user_id": 1,
            "created_at": created_at or utcnow(),
        }
    )


async def test_stats_counts_by_status_and_assignment(db) -> None:
    await _insert(db, status="open")
    await _insert(db, status="open", assignee_id=42)
    await _insert(db, status="closed")
    s = await repo.stats(db)
    assert s["open"] == 2
    assert s["closed"] == 1
    assert s["unassigned"] == 1  # only the open + no-assignee one
    assert s["total"] == 3
    assert s["today"] == 3


async def test_stats_empty(db) -> None:
    s = await repo.stats(db)
    assert s == {"open": 0, "closed": 0, "unassigned": 0, "total": 0, "today": 0}
