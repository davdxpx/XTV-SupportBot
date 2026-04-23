"""EventBus unit tests."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from xtv_support.core.events import EventBus
from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class _TicketMade(DomainEvent):
    ticket_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _VipTicketMade(_TicketMade):
    vip: bool = True


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


async def test_sync_and_async_handlers_both_receive_event(bus: EventBus) -> None:
    calls: list[str] = []

    def sync_handler(e: _TicketMade) -> None:
        calls.append(f"sync:{e.ticket_id}")

    async def async_handler(e: _TicketMade) -> None:
        calls.append(f"async:{e.ticket_id}")

    bus.subscribe(_TicketMade, sync_handler)
    bus.subscribe(_TicketMade, async_handler)

    await bus.publish(_TicketMade(ticket_id="t1"))

    assert sorted(calls) == ["async:t1", "sync:t1"]


async def test_decorator_registers_handler(bus: EventBus) -> None:
    received: list[str] = []

    @bus.on(_TicketMade)
    async def handler(e: _TicketMade) -> None:
        received.append(e.ticket_id)

    await bus.publish(_TicketMade(ticket_id="abc"))
    assert received == ["abc"]


async def test_failing_handler_does_not_block_siblings(bus: EventBus) -> None:
    good_calls: list[str] = []

    def boom(_e: _TicketMade) -> None:
        raise RuntimeError("boom")

    async def ok(e: _TicketMade) -> None:
        good_calls.append(e.ticket_id)

    bus.subscribe(_TicketMade, boom)
    bus.subscribe(_TicketMade, ok)

    # publish must not raise even though boom does
    await bus.publish(_TicketMade(ticket_id="keep-going"))
    assert good_calls == ["keep-going"]


async def test_failing_async_handler_is_contained(bus: EventBus) -> None:
    good_calls: list[str] = []

    async def boom(_e: _TicketMade) -> None:
        raise ValueError("async-boom")

    async def ok(e: _TicketMade) -> None:
        good_calls.append(e.ticket_id)

    bus.subscribe(_TicketMade, boom)
    bus.subscribe(_TicketMade, ok)

    await bus.publish(_TicketMade(ticket_id="still-ok"))
    assert good_calls == ["still-ok"]


async def test_unsubscribe_removes_handler(bus: EventBus) -> None:
    received: list[str] = []

    def handler(e: _TicketMade) -> None:
        received.append(e.ticket_id)

    bus.subscribe(_TicketMade, handler)
    assert bus.unsubscribe(_TicketMade, handler) is True
    await bus.publish(_TicketMade(ticket_id="x"))
    assert received == []


def test_unsubscribe_unknown_handler_returns_false(bus: EventBus) -> None:
    def handler(_e: _TicketMade) -> None: ...

    assert bus.unsubscribe(_TicketMade, handler) is False


async def test_duplicate_subscription_is_idempotent(bus: EventBus) -> None:
    calls: list[str] = []

    def handler(e: _TicketMade) -> None:
        calls.append(e.ticket_id)

    bus.subscribe(_TicketMade, handler)
    bus.subscribe(_TicketMade, handler)
    bus.subscribe(_TicketMade, handler)

    assert bus.handler_count(_TicketMade) == 1
    await bus.publish(_TicketMade(ticket_id="once"))
    assert calls == ["once"]


async def test_publish_with_no_subscribers_is_noop(bus: EventBus) -> None:
    # Must not raise or await forever.
    await bus.publish(_TicketMade(ticket_id="silent"))


async def test_propagate_to_bases_delivers_subclass_to_base_handler(bus: EventBus) -> None:
    base_hits: list[str] = []
    sub_hits: list[str] = []

    def on_base(e: _TicketMade) -> None:
        base_hits.append(e.ticket_id)

    def on_sub(e: _VipTicketMade) -> None:
        sub_hits.append(e.ticket_id)

    bus.subscribe(_TicketMade, on_base)
    bus.subscribe(_VipTicketMade, on_sub)

    # Without propagation: only subclass handler fires.
    await bus.publish(_VipTicketMade(ticket_id="v1"))
    assert sub_hits == ["v1"]
    assert base_hits == []

    # With propagation: both fire.
    await bus.publish(_VipTicketMade(ticket_id="v2"), propagate_to_bases=True)
    assert sub_hits == ["v1", "v2"]
    assert base_hits == ["v2"]


def test_clear_removes_all_handlers(bus: EventBus) -> None:
    bus.subscribe(_TicketMade, lambda _e: None)
    bus.subscribe(_VipTicketMade, lambda _e: None)
    assert bus.handler_count() == 2
    bus.clear()
    assert bus.handler_count() == 0
