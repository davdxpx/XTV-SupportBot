"""Dispatcher tests — patches the DB layer + the bus."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from xtv_support.domain.events import TicketRoutedToTeam
from xtv_support.domain.models.team import QueueRule, Team
from xtv_support.services.teams import dispatcher as disp


@pytest.fixture
def bus() -> AsyncMock:
    mock = AsyncMock()
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
def db() -> SimpleNamespace:
    return SimpleNamespace(tickets=SimpleNamespace(update_one=AsyncMock()))


@pytest.fixture
def _patch_teams_repo(monkeypatch: pytest.MonkeyPatch):
    mock = AsyncMock()
    monkeypatch.setattr(disp.teams_repo, "list_all", mock, raising=True)
    return mock


async def test_no_teams_configured_returns_none(db, bus, _patch_teams_repo) -> None:
    _patch_teams_repo.return_value = []
    result = await disp.assign_to_team(db, bus, {"_id": "t1"})
    assert result.team is None
    bus.publish.assert_not_awaited()


async def test_routes_and_emits_event(db, bus, _patch_teams_repo) -> None:
    team = Team(
        id="support",
        name="Support",
        queue_rules=(QueueRule(match={"tag": "vip"}, weight=200),),
    )
    _patch_teams_repo.return_value = [team]

    result = await disp.assign_to_team(db, bus, {"_id": "ticket-1", "tags": ["vip"]})
    assert result.team is team

    # DB persists the team_id
    db.tickets.update_one.assert_awaited_once()
    call = db.tickets.update_one.await_args.args
    assert call[0] == {"_id": "ticket-1"}
    assert call[1] == {"$set": {"team_id": "support"}}

    # Bus receives a TicketRoutedToTeam event
    bus.publish.assert_awaited_once()
    event = bus.publish.await_args.args[0]
    assert isinstance(event, TicketRoutedToTeam)
    assert event.ticket_id == "ticket-1"
    assert event.team_id == "support"
    assert event.reason == "auto"


async def test_no_match_does_not_persist_or_emit(db, bus, _patch_teams_repo) -> None:
    team = Team(
        id="vip",
        name="VIP",
        queue_rules=(QueueRule(match={"tag": "vip"}, weight=200),),
    )
    _patch_teams_repo.return_value = [team]

    result = await disp.assign_to_team(db, bus, {"_id": "t1", "tags": ["regular"]})
    assert result.team is None
    db.tickets.update_one.assert_not_awaited()
    bus.publish.assert_not_awaited()


async def test_persist_false_emits_event_but_does_not_write(
    db, bus, _patch_teams_repo
) -> None:
    team = Team(id="s", name="S", queue_rules=(QueueRule(match={}, weight=1),))
    _patch_teams_repo.return_value = [team]

    result = await disp.assign_to_team(db, bus, {"_id": "t1"}, persist=False)
    assert result.team is team
    db.tickets.update_one.assert_not_awaited()
    bus.publish.assert_awaited_once()


async def test_persist_error_is_swallowed_and_event_still_fires(
    db, bus, _patch_teams_repo
) -> None:
    team = Team(id="s", name="S", queue_rules=(QueueRule(match={}, weight=1),))
    _patch_teams_repo.return_value = [team]
    db.tickets.update_one.side_effect = RuntimeError("mongo down")

    # Must not raise
    result = await disp.assign_to_team(db, bus, {"_id": "t1"})
    assert result.team is team
    # Event still published
    bus.publish.assert_awaited_once()
