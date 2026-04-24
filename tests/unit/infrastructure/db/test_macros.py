"""Macros repo tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from xtv_support.infrastructure.db import macros as repo
from xtv_support.infrastructure.db.macros import InvalidMacroNameError


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []
        self.find_one = AsyncMock()
        self.insert_one = AsyncMock()
        self.update_one = AsyncMock()
        self.delete_one = AsyncMock()

    def find(self, query=None):
        if query is None:
            docs = list(self.docs)
        else:
            docs = [d for d in self.docs if _matches(d, query)]
        return _AsyncCursor(docs)


class _AsyncCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._sorted_key = None

    def sort(self, key, direction=1):
        self._docs.sort(key=lambda d: d.get(key), reverse=direction == -1)
        return self

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def _matches(doc, query):
    for k, v in query.items():
        if k == "$or":
            if not any(_matches(doc, sub) for sub in v):
                return False
            continue
        if doc.get(k) != v:
            return False
    return True


@pytest.fixture
def db() -> SimpleNamespace:
    return SimpleNamespace(macros=_FakeCollection())


# ----------------------------------------------------------------------
# Name validation
# ----------------------------------------------------------------------
@pytest.mark.parametrize("good", ["greet", "reset_password", "ticket-v2", "a1"])
def test_validate_name_accepts(good: str) -> None:
    assert repo.validate_name(good) == good


@pytest.mark.parametrize("bad", ["", "BadCaps", "has space", "-leading", "x" * 33])
def test_validate_name_rejects(bad: str) -> None:
    with pytest.raises(InvalidMacroNameError):
        repo.validate_name(bad)


# ----------------------------------------------------------------------
# Create
# ----------------------------------------------------------------------
async def test_create_rejects_duplicate_in_same_scope(db) -> None:
    db.macros.find_one.return_value = {"name": "hi", "team_id": None}
    with pytest.raises(ValueError):
        await repo.create(db, name="hi", body="x", created_by=1)


async def test_create_inserts_with_timestamps(db) -> None:
    db.macros.find_one.return_value = None
    db.macros.insert_one.return_value = MagicMock(inserted_id="abc")

    m = await repo.create(
        db,
        name="greet",
        body="Hi {user_name}",
        team_id="support",
        tags=["welcome"],
        created_by=7,
    )
    db.macros.insert_one.assert_awaited_once()
    doc = db.macros.insert_one.await_args.args[0]
    assert doc["name"] == "greet"
    assert doc["team_id"] == "support"
    assert doc["tags"] == ["welcome"]
    assert "created_at" in doc and "updated_at" in doc
    assert m.name == "greet"
    assert m.scope == "team:support"


# ----------------------------------------------------------------------
# Lookup precedence
# ----------------------------------------------------------------------
async def test_get_by_name_prefers_team_scope(db) -> None:
    team_doc = {"_id": 1, "name": "hi", "team_id": "support", "body": "team"}
    global_doc = {"_id": 2, "name": "hi", "team_id": None, "body": "global"}

    async def side_effect(query):
        if query == {"name": "hi", "team_id": "support"}:
            return team_doc
        if query == {"name": "hi", "team_id": None}:
            return global_doc
        return None

    db.macros.find_one.side_effect = side_effect
    m = await repo.get_by_name(db, "hi", team_id="support")
    assert m is not None and m.body == "team"


async def test_get_by_name_falls_back_to_global(db) -> None:
    global_doc = {"_id": 2, "name": "hi", "team_id": None, "body": "global"}

    async def side_effect(query):
        if query == {"name": "hi", "team_id": "support"}:
            return None
        if query == {"name": "hi", "team_id": None}:
            return global_doc
        return None

    db.macros.find_one.side_effect = side_effect
    m = await repo.get_by_name(db, "hi", team_id="support")
    assert m is not None and m.body == "global"


async def test_get_by_name_returns_none_when_nothing_matches(db) -> None:
    db.macros.find_one.return_value = None
    assert await repo.get_by_name(db, "hi", team_id="support") is None


async def test_get_by_name_global_only_when_team_is_none(db) -> None:
    db.macros.find_one.return_value = {"_id": 3, "name": "hi", "team_id": None, "body": "g"}
    m = await repo.get_by_name(db, "hi", team_id=None)
    assert m is not None
    db.macros.find_one.assert_awaited_once_with({"name": "hi", "team_id": None})


# ----------------------------------------------------------------------
# Listing
# ----------------------------------------------------------------------
async def test_list_visible_team_and_global(db) -> None:
    db.macros.docs = [
        {"_id": 1, "name": "a", "team_id": None, "body": ""},
        {"_id": 2, "name": "b", "team_id": "support", "body": ""},
        {"_id": 3, "name": "c", "team_id": "billing", "body": ""},
    ]
    items = await repo.list_visible(db, team_id="support")
    assert {m.name for m in items} == {"a", "b"}


async def test_list_visible_global_only(db) -> None:
    db.macros.docs = [
        {"_id": 1, "name": "a", "team_id": None, "body": ""},
        {"_id": 2, "name": "b", "team_id": "support", "body": ""},
    ]
    items = await repo.list_visible(db, team_id=None)
    assert {m.name for m in items} == {"a"}


# ----------------------------------------------------------------------
# Usage counter
# ----------------------------------------------------------------------
async def test_increment_usage_triggers_update(db, monkeypatch) -> None:
    # ObjectId import is inside the function; inject a dummy one.
    import sys
    import types

    bson = types.SimpleNamespace(ObjectId=lambda s: f"oid:{s}")
    monkeypatch.setitem(sys.modules, "bson", bson)

    await repo.increment_usage(db, "raw-id")
    db.macros.update_one.assert_awaited_once()
    call = db.macros.update_one.await_args.args
    assert call[0] == {"_id": "oid:raw-id"}
    assert call[1] == {"$inc": {"usage_count": 1}}
