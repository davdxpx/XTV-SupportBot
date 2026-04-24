"""Roles repository tests.

Uses :class:`AsyncMock` for the Motor collection so we can assert
query / update shapes without bringing in mongomock.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from xtv_support.domain.enums import Role
from xtv_support.infrastructure.db import roles as repo


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []
        self.find_one = AsyncMock()
        self.update_one = AsyncMock()
        self.delete_one = AsyncMock()

    def find(self, query: dict | None = None) -> _AsyncCursor:
        return _AsyncCursor(self.docs if query is None else _filter(self.docs, query))


class _AsyncCursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = iter(docs)

    def __aiter__(self) -> _AsyncCursor:
        return self

    async def __anext__(self) -> dict:
        try:
            return next(self._docs)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def _filter(docs: list[dict], query: dict) -> list[dict]:
    out = []
    for d in docs:
        hit = True
        for k, v in query.items():
            if k == "team_ids":
                if v not in (d.get("team_ids") or []):
                    hit = False
                    break
            elif d.get(k) != v:
                hit = False
                break
        if hit:
            out.append(d)
    return out


@pytest.fixture
def db() -> SimpleNamespace:
    return SimpleNamespace(roles=_FakeCollection())


async def test_get_role_returns_none_when_missing(db) -> None:
    db.roles.find_one.return_value = None
    assert await repo.get_role(db, 42) is None


async def test_get_role_parses_doc(db) -> None:
    db.roles.find_one.return_value = {
        "user_id": 1,
        "role": "admin",
        "team_ids": ["t1", "t2"],
        "granted_by": 99,
    }
    a = await repo.get_role(db, 1)
    assert a is not None
    assert a.user_id == 1
    assert a.role is Role.ADMIN
    assert a.team_ids == ("t1", "t2")
    assert a.granted_by == 99


async def test_get_role_or_default_when_missing(db) -> None:
    db.roles.find_one.return_value = None
    a = await repo.get_role_or_default(db, 7)
    assert a.role is Role.USER
    assert a.user_id == 7


async def test_grant_upserts(db) -> None:
    await repo.grant(db, user_id=5, role=Role.AGENT, granted_by=1, team_ids=["support"])
    call = db.roles.update_one.await_args
    assert call is not None
    filter_, update = call.args
    assert filter_ == {"user_id": 5}
    assert update["$set"]["role"] == "agent"
    assert update["$set"]["team_ids"] == ["support"]
    assert update["$set"]["granted_by"] == 1
    assert update["$setOnInsert"] == {"user_id": 5}
    assert call.kwargs.get("upsert") is True


async def test_grant_without_team_ids_does_not_set_field(db) -> None:
    await repo.grant(db, user_id=5, role=Role.AGENT, granted_by=1)
    _, update = db.roles.update_one.await_args.args
    assert "team_ids" not in update["$set"]


async def test_revoke_deletes(db) -> None:
    await repo.revoke(db, 5)
    db.roles.delete_one.assert_awaited_once_with({"user_id": 5})


async def test_list_by_role(db) -> None:
    db.roles.docs = [
        {"user_id": 1, "role": "admin", "team_ids": []},
        {"user_id": 2, "role": "agent", "team_ids": []},
        {"user_id": 3, "role": "admin", "team_ids": []},
    ]
    admins = await repo.list_by_role(db, Role.ADMIN)
    assert {a.user_id for a in admins} == {1, 3}


async def test_list_by_team(db) -> None:
    db.roles.docs = [
        {"user_id": 1, "role": "agent", "team_ids": ["support"]},
        {"user_id": 2, "role": "agent", "team_ids": ["billing"]},
        {"user_id": 3, "role": "agent", "team_ids": ["support", "billing"]},
    ]
    support = await repo.list_by_team(db, "support")
    assert {a.user_id for a in support} == {1, 3}


async def test_add_and_remove_from_team(db) -> None:
    await repo.add_to_team(db, 5, "support")
    call = db.roles.update_one.await_args
    filter_, update = call.args
    assert filter_ == {"user_id": 5}
    assert update == {"$addToSet": {"team_ids": "support"}}

    await repo.remove_from_team(db, 5, "support")
    call = db.roles.update_one.await_args
    _, update = call.args
    assert update == {"$pull": {"team_ids": "support"}}
