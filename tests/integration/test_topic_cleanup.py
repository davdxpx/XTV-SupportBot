"""Phase C — auto-delete forum topics of long-closed tickets.

The repo query runs against mongomock directly. ``run_once`` imports pyrogram
via the topic service, so we stub both the ``pyrogram`` module and the topic
service before importing the task — that keeps the selection + clear-topic
wiring testable in the sandbox.
"""

from __future__ import annotations

import asyncio
import sys
import types
from datetime import timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient

from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.utils.time import utcnow

_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


def _insert(db, **fields) -> None:
    _run(db.tickets.insert_one(fields))


def test_find_closed_topics_before_selects_correctly() -> None:
    db = AsyncMongoMockClient().testdb
    now = utcnow()
    _insert(db, status="closed", topic_id=1, closed_at=now - timedelta(hours=48))  # old → yes
    _insert(db, status="closed", topic_id=2, closed_at=now - timedelta(minutes=5))  # fresh → no
    _insert(db, status="open", topic_id=3, closed_at=None)  # open → no
    _insert(
        db, status="closed", topic_id=None, closed_at=now - timedelta(hours=48)
    )  # no topic → no

    found = _run(tickets_repo.find_closed_topics_before(db, threshold=timedelta(minutes=1440)))
    assert {t["topic_id"] for t in found} == {1}


def test_clear_topic_nulls_topic_id() -> None:
    db = AsyncMongoMockClient().testdb
    tid = _run(tickets_repo.create(db, project_id=None, user_id=7, message="x"))
    _run(tickets_repo.set_topic(db, tid, topic_id=99, fallback=False))
    _run(tickets_repo.clear_topic(db, tid))
    doc = _run(tickets_repo.get(db, tid))
    assert doc["topic_id"] is None
    assert doc.get("topic_deleted_at") is not None


@pytest.fixture
def task(monkeypatch):
    """Import the cleanup task with pyrogram + topic_service stubbed out."""
    deleted: list[int] = []

    fake_pyrogram = types.ModuleType("pyrogram")
    fake_pyrogram.Client = object
    monkeypatch.setitem(sys.modules, "pyrogram", fake_pyrogram)

    fake_ts = types.ModuleType("xtv_support.services.tickets.topic_service")

    async def delete_topic(_client, topic_id):  # noqa: ANN001
        deleted.append(topic_id)
        return True

    fake_ts.delete_topic = delete_topic
    monkeypatch.setitem(sys.modules, "xtv_support.services.tickets.topic_service", fake_ts)
    monkeypatch.delitem(sys.modules, "xtv_support.tasks.topic_cleanup_task", raising=False)

    from xtv_support.config import runtime

    runtime.invalidate()  # don't inherit another test's cached overrides

    from xtv_support.tasks import topic_cleanup_task

    yield topic_cleanup_task, deleted

    runtime.invalidate()
    # Drop the fake-bound module so a later test re-imports it against the real
    # pyrogram / topic service (matters on CI, where both are installed).
    sys.modules.pop("xtv_support.tasks.topic_cleanup_task", None)


def test_run_once_deletes_and_clears(task, monkeypatch) -> None:
    mod, deleted = task
    from xtv_support.config import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "TOPIC_DELETE_AFTER_CLOSE_MINUTES", 60)

    db = AsyncMongoMockClient().testdb
    _insert(db, status="closed", topic_id=42, closed_at=utcnow() - timedelta(hours=3))

    n = _run(mod.run_once(object(), db))
    assert n == 1
    assert deleted == [42]
    doc = _run(db.tickets.find_one({"topic_id": {"$exists": True}}))
    # topic_id is cleared after deletion
    assert doc is not None and doc["topic_id"] is None


def test_run_once_disabled_is_noop(task, monkeypatch) -> None:
    mod, deleted = task
    from xtv_support.config import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "TOPIC_DELETE_AFTER_CLOSE_MINUTES", 0)

    db = AsyncMongoMockClient().testdb
    _insert(db, status="closed", topic_id=42, closed_at=utcnow() - timedelta(days=99))

    assert _run(mod.run_once(object(), db)) == 0
    assert deleted == []
