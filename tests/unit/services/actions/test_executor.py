"""ActionExecutor unit tests — patch the lazy repo accessors so no Mongo is needed."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from xtv_support.domain.events.actions import ActionExecuted, ActionFailed
from xtv_support.services.actions.executor import ActionContext, ActionExecutor


def _run(coro):
    return asyncio.run(coro)


class _Bus:
    def __init__(self) -> None:
        self.published: list[Any] = []

    async def publish(self, event: Any) -> None:
        self.published.append(event)


class _FakeTicketsColl:
    def __init__(self) -> None:
        self.updates: list[tuple[dict, dict]] = []

    async def update_one(self, filt: dict, update: dict, **kw: Any) -> Any:
        self.updates.append((filt, update))

        class _R:
            matched_count = 1

        return _R()


class _FakeDB:
    def __init__(self) -> None:
        self.tickets = _FakeTicketsColl()


def test_unknown_action_emits_failed() -> None:
    bus = _Bus()
    ctx = ActionContext(db=_FakeDB(), bus=bus, actor_id=7, origin="bot")
    executor = ActionExecutor()

    result = _run(executor.execute(ctx, "nope", ticket_id=None))

    assert result.ok is False
    assert result.detail == "unknown_action"
    assert any(isinstance(ev, ActionFailed) for ev in bus.published)


def test_close_action_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    bus = _Bus()
    db = _FakeDB()
    ticket = {"_id": "t1", "status": "open", "tags": []}

    class _FakeRepo:
        @staticmethod
        async def get(_db: Any, _id: str) -> dict | None:
            return ticket if _id == "t1" else None

        @staticmethod
        async def close(_db: Any, _id: str, **kw: Any) -> None:
            ticket["status"] = "closed"

        assign = close
        set_priority = close

    import xtv_support.services.actions.executor as mod

    monkeypatch.setattr(mod, "_tickets_repo", lambda: _FakeRepo)

    ctx = ActionContext(db=db, bus=bus, actor_id=7, origin="bot")
    executor = ActionExecutor()

    result = _run(executor.execute(ctx, "close", ticket_id="t1", params={"reason": "resolved"}))

    assert result.ok
    assert ticket["status"] == "closed"
    assert any(isinstance(ev, ActionExecuted) and ev.action == "close" for ev in bus.published)


def test_add_internal_note_requires_text(monkeypatch: pytest.MonkeyPatch) -> None:
    bus = _Bus()
    ticket = {"_id": "t1", "internal_notes": []}

    class _FakeRepo:
        @staticmethod
        async def get(_db: Any, _id: str) -> dict | None:
            return ticket

    import xtv_support.services.actions.executor as mod

    monkeypatch.setattr(mod, "_tickets_repo", lambda: _FakeRepo)

    ctx = ActionContext(db=_FakeDB(), bus=bus, actor_id=1, origin="bot")
    executor = ActionExecutor()

    res = _run(executor.execute(ctx, "add_internal_note", ticket_id="t1", params={"text": ""}))
    assert res.ok is False
    assert res.detail == "text_required"
