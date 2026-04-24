"""Finite-state-machine registry + pluggable state store.

Replaces the implicit state-keeping that lives today inside
``handlers/admin/input_router.py`` and the ``UserState`` enum in
``core/constants.py``. The FSM itself remains simple — a per-user
string-valued state, optionally with a TTL — but the store behind it is
pluggable (in-memory for tests, Mongo in production, Redis when
``REDIS_URL`` is set).

Design choices
--------------
* **Key is always an ``int``** (Telegram user id). Services that need
  per-chat or per-ticket FSMs can prefix the state value or derive a
  custom key via :meth:`StateStore.namespaced`.
* **Values are strings** — the existing :class:`UserState` enum
  (``xtv_support.core.constants.UserState``) is a ``StrEnum`` so it
  slots in unchanged.
* **Expiry is optional** — admin wizards can pass ``ttl_seconds`` so a
  crashed wizard self-recovers; regular handlers leave it ``None``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class StateEntry:
    """Serialised state snapshot."""

    value: str
    data: Mapping[str, object] = field(default_factory=dict)
    expires_at: float | None = None  # epoch seconds, None = never

    def is_expired(self, *, now: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now if now is not None else time.time()) >= self.expires_at


@runtime_checkable
class StateStore(Protocol):
    """Persistent backend for :class:`StateMachine`."""

    async def get(self, key: int) -> StateEntry | None: ...
    async def set(self, key: int, entry: StateEntry) -> None: ...
    async def clear(self, key: int) -> None: ...


class MemoryStateStore:
    """In-process store. Perfect for unit tests and single-instance bots."""

    __slots__ = ("_data", "_lock")

    def __init__(self) -> None:
        self._data: dict[int, StateEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: int) -> StateEntry | None:
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._data[key]
                return None
            return entry

    async def set(self, key: int, entry: StateEntry) -> None:
        async with self._lock:
            self._data[key] = entry

    async def clear(self, key: int) -> None:
        async with self._lock:
            self._data.pop(key, None)

    # Useful in tests only.
    def _snapshot(self) -> dict[int, StateEntry]:
        return dict(self._data)


class StateMachine:
    """Tiny FSM facade over a :class:`StateStore`."""

    __slots__ = ("_store",)

    def __init__(self, store: StateStore) -> None:
        self._store = store

    async def current(self, user_id: int) -> str | None:
        entry = await self._store.get(user_id)
        return None if entry is None else entry.value

    async def data(self, user_id: int) -> Mapping[str, object]:
        entry = await self._store.get(user_id)
        return {} if entry is None else dict(entry.data)

    async def set(
        self,
        user_id: int,
        value: str,
        *,
        data: Mapping[str, object] | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        entry = StateEntry(
            value=value,
            data=dict(data) if data else {},
            expires_at=expires_at,
        )
        await self._store.set(user_id, entry)

    async def clear(self, user_id: int) -> None:
        await self._store.clear(user_id)

    async def transition(
        self,
        user_id: int,
        *,
        expected: str | None,
        to: str,
        data: Mapping[str, object] | None = None,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Compare-and-set — move ``user_id`` from ``expected`` to ``to``.

        Returns True when the transition was applied, False when the
        current state did not match ``expected``.
        """
        current = await self.current(user_id)
        if current != expected:
            return False
        await self.set(user_id, to, data=data, ttl_seconds=ttl_seconds)
        return True

    async def merge_data(self, user_id: int, **updates: object) -> None:
        """Merge ``updates`` into the current state's data bag (preserves value / expiry)."""
        entry = await self._store.get(user_id)
        if entry is None:
            return
        merged = {**dict(entry.data), **updates}
        new_entry = StateEntry(value=entry.value, data=merged, expires_at=entry.expires_at)
        await self._store.set(user_id, new_entry)
