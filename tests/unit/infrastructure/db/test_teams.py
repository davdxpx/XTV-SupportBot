"""Teams repository tests."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from xtv_support.domain.enums import Weekday
from xtv_support.domain.models.team import BusinessHoursWindow, QueueRule, Team
from xtv_support.infrastructure.db import teams as repo
from xtv_support.infrastructure.db.teams import InvalidSlugError


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []
        self.find_one = AsyncMock()
        self.insert_one = AsyncMock()
        self.update_one = AsyncMock()
        self.delete_one = AsyncMock()

    def find(self, query: dict | None = None) -> "_AsyncCursor":
        if query is None:
            return _AsyncCursor(list(self.docs))
        out = []
        for d in self.docs:
            if all((k in ("member_ids",) and v in (d.get(k) or [])) or d.get(k) == v
                   for k, v in query.items()):
                out.append(d)
        return _AsyncCursor(out)


class _AsyncCursor:
    def __init__(self, docs: list[dict]) -> None:
        self._it = iter(docs)

    def __aiter__(self) -> "_AsyncCursor":
        return self

    async def __anext__(self) -> dict:
        try:
            return next(self._it)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@pytest.fixture
def db() -> SimpleNamespace:
    return SimpleNamespace(teams=_FakeCollection())


# ------------------------------------------------------------------
# Slug validation
# ------------------------------------------------------------------
@pytest.mark.parametrize("ok", ["support", "support-tier1", "a", "billing_2024"])
def test_validate_slug_accepts(ok: str) -> None:
    assert repo.validate_slug(ok) == ok


@pytest.mark.parametrize("bad", ["", "Has Spaces", "-leadhyphen", "CAPS", "a" * 33])
def test_validate_slug_rejects(bad: str) -> None:
    with pytest.raises(InvalidSlugError):
        repo.validate_slug(bad)


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------
async def test_create_inserts_and_returns_team(db) -> None:
    team = await repo.create(
        db, team_id="support", name="Support", timezone="Europe/Berlin", created_by=99
    )
    assert isinstance(team, Team)
    assert team.id == "support"
    assert team.timezone == "Europe/Berlin"
    db.teams.insert_one.assert_awaited_once()
    doc = db.teams.insert_one.await_args.args[0]
    assert doc["_id"] == "support"
    assert doc["created_by"] == 99


async def test_get_returns_none_when_missing(db) -> None:
    db.teams.find_one.return_value = None
    assert await repo.get(db, "nope") is None


async def test_get_parses_doc(db) -> None:
    db.teams.find_one.return_value = {
        "_id": "support",
        "name": "Support",
        "timezone": "UTC",
        "business_hours": [{"weekday": 0, "start": "09:00", "end": "18:00"}],
        "holidays": ["2026-12-24"],
        "member_ids": [1, 2, 3],
        "queue_rules": [{"match": {"tag": "vip"}, "weight": 200}],
        "created_by": 99,
    }
    t = await repo.get(db, "support")
    assert t is not None
    assert t.name == "Support"
    assert t.member_ids == (1, 2, 3)
    assert t.holidays == ("2026-12-24",)
    assert t.business_hours[0].weekday is Weekday.MONDAY
    assert t.queue_rules[0].match == {"tag": "vip"}
    assert t.queue_rules[0].weight == 200


async def test_list_all(db) -> None:
    db.teams.docs = [
        {"_id": "a", "name": "A"},
        {"_id": "b", "name": "B"},
    ]
    teams = await repo.list_all(db)
    assert {t.id for t in teams} == {"a", "b"}


async def test_list_for_member(db) -> None:
    db.teams.docs = [
        {"_id": "a", "name": "A", "member_ids": [1, 2]},
        {"_id": "b", "name": "B", "member_ids": [3]},
        {"_id": "c", "name": "C", "member_ids": [2, 3]},
    ]
    teams = await repo.list_for_member(db, 2)
    assert {t.id for t in teams} == {"a", "c"}


async def test_delete_reports_result(db) -> None:
    db.teams.delete_one.return_value = SimpleNamespace(deleted_count=1)
    assert await repo.delete(db, "a") is True

    db.teams.delete_one.return_value = SimpleNamespace(deleted_count=0)
    assert await repo.delete(db, "b") is False


async def test_add_and_remove_member(db) -> None:
    await repo.add_member(db, "support", 5)
    _, update = db.teams.update_one.await_args.args
    assert update == {"$addToSet": {"member_ids": 5}}

    await repo.remove_member(db, "support", 5)
    _, update = db.teams.update_one.await_args.args
    assert update == {"$pull": {"member_ids": 5}}


async def test_set_business_hours_serialises_windows(db) -> None:
    windows = [
        BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="18:00"),
        BusinessHoursWindow(weekday=Weekday.FRIDAY, start="09:00", end="15:00"),
    ]
    await repo.set_business_hours(db, "support", windows)
    _, update = db.teams.update_one.await_args.args
    assert update["$set"]["business_hours"] == [
        {"weekday": 0, "start": "09:00", "end": "18:00"},
        {"weekday": 4, "start": "09:00", "end": "15:00"},
    ]


async def test_set_queue_rules_serialises(db) -> None:
    rules = [
        QueueRule(match={"tag": "vip"}, weight=200),
        QueueRule(match={"project_type": "feedback"}, weight=50),
    ]
    await repo.set_queue_rules(db, "support", rules)
    _, update = db.teams.update_one.await_args.args
    assert update["$set"]["queue_rules"] == [
        {"match": {"tag": "vip"}, "weight": 200},
        {"match": {"project_type": "feedback"}, "weight": 50},
    ]


async def test_set_holidays_copies_list(db) -> None:
    await repo.set_holidays(db, "support", ["2026-01-01", "2026-12-24"])
    _, update = db.teams.update_one.await_args.args
    assert update["$set"]["holidays"] == ["2026-01-01", "2026-12-24"]


async def test_rename_and_set_timezone(db) -> None:
    await repo.rename(db, "support", "Support Tier 1")
    _, update = db.teams.update_one.await_args.args
    assert update == {"$set": {"name": "Support Tier 1"}}

    await repo.set_timezone(db, "support", "Europe/Berlin")
    _, update = db.teams.update_one.await_args.args
    assert update == {"$set": {"timezone": "Europe/Berlin"}}
