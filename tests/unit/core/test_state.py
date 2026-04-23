"""StateMachine + MemoryStateStore tests."""
from __future__ import annotations

import asyncio
import time

import pytest

from xtv_support.core.state import MemoryStateStore, StateEntry, StateMachine


@pytest.fixture
def fsm() -> StateMachine:
    return StateMachine(MemoryStateStore())


async def test_current_is_none_when_unset(fsm: StateMachine) -> None:
    assert await fsm.current(1) is None
    assert await fsm.data(1) == {}


async def test_set_and_get(fsm: StateMachine) -> None:
    await fsm.set(7, "awaiting_feedback", data={"project": "abc"})
    assert await fsm.current(7) == "awaiting_feedback"
    assert await fsm.data(7) == {"project": "abc"}


async def test_clear(fsm: StateMachine) -> None:
    await fsm.set(7, "state-a")
    await fsm.clear(7)
    assert await fsm.current(7) is None


async def test_transition_respects_expected_state(fsm: StateMachine) -> None:
    await fsm.set(9, "stage1")
    ok = await fsm.transition(9, expected="stage1", to="stage2")
    assert ok is True
    assert await fsm.current(9) == "stage2"


async def test_transition_rejects_when_mismatch(fsm: StateMachine) -> None:
    await fsm.set(9, "stage1")
    ok = await fsm.transition(9, expected="does-not-match", to="stage2")
    assert ok is False
    assert await fsm.current(9) == "stage1"


async def test_transition_from_none_works(fsm: StateMachine) -> None:
    ok = await fsm.transition(9, expected=None, to="start")
    assert ok is True
    assert await fsm.current(9) == "start"


async def test_merge_data_updates_existing_bag(fsm: StateMachine) -> None:
    await fsm.set(1, "wiz", data={"a": 1})
    await fsm.merge_data(1, b=2, a=3)  # a is overridden, b is added
    assert await fsm.data(1) == {"a": 3, "b": 2}
    assert await fsm.current(1) == "wiz"


async def test_merge_data_on_unset_user_is_noop(fsm: StateMachine) -> None:
    await fsm.merge_data(42, foo="bar")
    assert await fsm.current(42) is None


async def test_ttl_expires_entry(fsm: StateMachine) -> None:
    await fsm.set(1, "quick", ttl_seconds=1)
    # Force expiry instead of sleeping 1s
    store: MemoryStateStore = fsm._store  # type: ignore[assignment]
    snap = store._snapshot()[1]
    expired = StateEntry(value=snap.value, data=snap.data, expires_at=time.time() - 1)
    await store.set(1, expired)
    assert await fsm.current(1) is None


async def test_memory_store_is_concurrent_safe() -> None:
    store = MemoryStateStore()
    fsm = StateMachine(store)
    async def worker(uid: int) -> None:
        await fsm.set(uid, f"s{uid}")
    await asyncio.gather(*(worker(i) for i in range(50)))
    snap = store._snapshot()
    assert len(snap) == 50
    assert snap[10].value == "s10"
