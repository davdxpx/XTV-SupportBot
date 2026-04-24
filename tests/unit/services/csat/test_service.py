"""CSAT service tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from xtv_support.domain.events import CsatReceived
from xtv_support.services.csat.service import (
    MAX_SCORE,
    MIN_SCORE,
    InvalidScoreError,
    aggregate_stats,
    record_rating,
    validate_score,
)


# ----------------------------------------------------------------------
# validate_score
# ----------------------------------------------------------------------
@pytest.mark.parametrize("s", [1, 2, 3, 4, 5])
def test_validate_score_accepts_full_range(s: int) -> None:
    assert validate_score(s) == s


@pytest.mark.parametrize("bad", [0, 6, -1, 100, 1.5, "3", None])
def test_validate_score_rejects_everything_else(bad) -> None:
    with pytest.raises(InvalidScoreError):
        validate_score(bad)


def test_score_bounds_constants() -> None:
    assert MIN_SCORE == 1
    assert MAX_SCORE == 5


# ----------------------------------------------------------------------
# record_rating
# ----------------------------------------------------------------------
class _CsatColl:
    def __init__(self) -> None:
        self.update_one = AsyncMock()
        self.find_one = AsyncMock(return_value=None)

    def find(self, query=None, projection=None):
        return _EmptyCursor()


class _EmptyCursor:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


@pytest.fixture
def db() -> SimpleNamespace:
    return SimpleNamespace(csat_responses=_CsatColl())


async def test_record_rating_persists_and_emits(db) -> None:
    bus = SimpleNamespace(publish=AsyncMock())
    await record_rating(
        db,
        bus,
        ticket_id="t1",
        user_id=99,
        score=5,
        team_id="support",
    )
    # Upsert on (ticket_id, user_id).
    db.csat_responses.update_one.assert_awaited_once()
    call = db.csat_responses.update_one.await_args.args
    assert call[0] == {"ticket_id": "t1", "user_id": 99}
    assert call[1]["$set"]["score"] == 5
    assert call[1]["$set"]["team_id"] == "support"
    # Event published.
    bus.publish.assert_awaited_once()
    ev = bus.publish.await_args.args[0]
    assert isinstance(ev, CsatReceived)
    assert ev.score == 5


async def test_record_rating_rejects_invalid_score(db) -> None:
    bus = SimpleNamespace(publish=AsyncMock())
    with pytest.raises(InvalidScoreError):
        await record_rating(db, bus, ticket_id="t1", user_id=1, score=6)


async def test_record_rating_swallows_db_errors(db) -> None:
    bus = SimpleNamespace(publish=AsyncMock())
    db.csat_responses.update_one.side_effect = RuntimeError("mongo down")
    # Must not raise; event is NOT emitted when persist fails.
    await record_rating(db, bus, ticket_id="t1", user_id=1, score=4)
    bus.publish.assert_not_awaited()


async def test_record_rating_with_none_bus(db) -> None:
    await record_rating(
        db,
        None,
        ticket_id="t1",
        user_id=1,
        score=3,
    )
    db.csat_responses.update_one.assert_awaited_once()


# ----------------------------------------------------------------------
# aggregate_stats
# ----------------------------------------------------------------------
class _AggColl:
    def __init__(self, docs):
        self.docs = list(docs)

    def find(self, query=None, projection=None):
        return _AggCursor(self.docs)


class _AggCursor:
    def __init__(self, docs):
        self._it = iter(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


async def test_aggregate_stats_empty() -> None:
    db = SimpleNamespace(csat_responses=_AggColl([]))
    s = await aggregate_stats(db)
    assert s.responses == 0
    assert s.average == 0.0
    assert s.promoter_share == 0.0
    assert s.distribution == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}


async def test_aggregate_stats_summary() -> None:
    db = SimpleNamespace(
        csat_responses=_AggColl(
            [
                {"score": 5},
                {"score": 5},
                {"score": 4},
                {"score": 3},
                {"score": 2},
                {"score": 1},
            ]
        )
    )
    s = await aggregate_stats(db)
    assert s.responses == 6
    assert s.average == round((5 + 5 + 4 + 3 + 2 + 1) / 6, 2)
    assert s.distribution == {1: 1, 2: 1, 3: 1, 4: 1, 5: 2}
    assert s.promoters == 3  # 5, 5, 4
    assert s.detractors == 2  # 2, 1
    assert s.promoter_share == round(3 / 6, 3)


async def test_aggregate_stats_ignores_out_of_range_scores() -> None:
    db = SimpleNamespace(
        csat_responses=_AggColl(
            [
                {"score": 5},
                {"score": 9},
                {"score": 0},
                {"score": 4},
            ]
        )
    )
    s = await aggregate_stats(db)
    assert s.responses == 2  # 5 and 4
    assert s.distribution == {1: 0, 2: 0, 3: 0, 4: 1, 5: 1}
