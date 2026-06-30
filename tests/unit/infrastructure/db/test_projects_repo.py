"""projects repo helpers added in Phase 2: update + id/slug resolver."""

from __future__ import annotations

import pytest
from mongomock_motor import AsyncMongoMockClient

from xtv_support.infrastructure.db import projects as repo
from xtv_support.infrastructure.db import tickets as tickets_repo


@pytest.fixture
def db():
    return AsyncMongoMockClient().testdb


async def test_update_whitelists_fields(db) -> None:
    pid = await repo.create(db, name="A", description="d", created_by=1)
    ok = await repo.update(db, pid, {"name": "B", "evil": "x", "active": False})
    assert ok is True
    doc = await repo.get(db, pid)
    assert doc["name"] == "B"
    assert "evil" not in doc  # not whitelisted
    assert doc["active"] is True  # 'active' is not editable via update()


async def test_update_no_editable_fields_returns_false(db) -> None:
    pid = await repo.create(db, name="A", description="d", created_by=1)
    assert await repo.update(db, pid, {"evil": "x"}) is False


async def test_get_by_id_or_slug(db) -> None:
    pid = await repo.create(db, name="A", description="d", created_by=1)
    await db.projects.update_one({"_id": pid}, {"$set": {"slug": "alpha"}})
    assert (await repo.get_by_id_or_slug(db, str(pid)))["name"] == "A"
    assert (await repo.get_by_id_or_slug(db, "alpha"))["name"] == "A"
    assert await repo.get_by_id_or_slug(db, "missing") is None


async def test_tickets_count_by_project(db) -> None:
    pid = await repo.create(db, name="A", description="d", created_by=1)
    await tickets_repo.create(db, project_id=str(pid), user_id=1, message="m")
    await tickets_repo.create(db, project_id=str(pid), user_id=2, message="m2")
    assert await tickets_repo.count_by_project(db, str(pid)) == 2
    assert await tickets_repo.count_by_project(db, "missing") == 0
