"""Typed callback-data v2 — generic, versioned, with overflow handling.

``core/callback_data.py`` (v1) hard-codes one dataclass per concrete
button prefix. That's fine for stable flows like ``/close`` or the
rating buttons, but the v1.0 overhaul (agent inbox, admin panel, rule
builder) needs a scheme where any handler can emit a short, typed
payload without adding a new class. v2 gives us:

- ``cb:v2:<namespace>:<action>[:<arg>…]`` — a fixed scheme a single
  dispatcher can parse.
- Overflow escape: payloads > 64 bytes (Telegram's limit) are stored
  in an LRU :class:`InMemoryCallbackStore` keyed by a short blake2s
  hash. The button carries only ``cb:v2:ov:<hash>``; resolvers decode
  back transparently.
- Co-existence: v1 callbacks are untouched. A v2 parser returns
  ``None`` for anything that doesn't start with ``cb:v2:``, so the
  existing routers keep working during the migration.

Production runs with multiple replicas should back the store with
Redis; the default in-memory LRU is fine for the single-replica
deploy model we support today.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol

PREFIX = "cb:v2"
OVERFLOW_PREFIX = f"{PREFIX}:ov"
MAX_CALLBACK_BYTES = 64


@dataclass(frozen=True, slots=True)
class Callback:
    namespace: str
    action: str
    args: tuple[str, ...] = ()

    def encode(self) -> str:
        parts = [PREFIX, self.namespace, self.action, *self.args]
        return ":".join(parts)


class CallbackStore(Protocol):
    async def put(self, payload: str) -> str: ...
    async def get(self, key: str) -> str | None: ...


class InMemoryCallbackStore:
    """Bounded LRU store. Safe default for single-replica deploys."""

    def __init__(self, max_entries: int = 10_000, ttl_seconds: int = 3600) -> None:
        self._max = max_entries
        self._ttl = ttl_seconds
        self._items: OrderedDict[str, tuple[str, float]] = OrderedDict()

    async def put(self, payload: str) -> str:
        key = hashlib.blake2s(payload.encode(), digest_size=8).hexdigest()
        now = time.monotonic()
        self._items[key] = (payload, now)
        self._items.move_to_end(key)
        while len(self._items) > self._max:
            self._items.popitem(last=False)
        return key

    async def get(self, key: str) -> str | None:
        item = self._items.get(key)
        if item is None:
            return None
        payload, ts = item
        if (time.monotonic() - ts) > self._ttl:
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return payload


def build(namespace: str, action: str, *args: str | int) -> Callback:
    return Callback(namespace=namespace, action=action, args=tuple(str(a) for a in args))


def parse(raw: str) -> Callback | None:
    """Return the typed callback or ``None`` if the prefix is foreign."""
    if not raw or not raw.startswith(f"{PREFIX}:"):
        return None
    parts = raw.split(":")
    if len(parts) < 4:
        return None
    return Callback(namespace=parts[2], action=parts[3], args=tuple(parts[4:]))


async def encode_safe(cb: Callback, store: CallbackStore) -> str:
    """Encode the callback, spilling into ``store`` if over 64 bytes."""
    raw = cb.encode()
    if len(raw.encode()) <= MAX_CALLBACK_BYTES:
        return raw
    key = await store.put(raw)
    # The short form is guaranteed <= 64 bytes: prefix (8) + ":ov:" (4) + 16 hex.
    return f"{OVERFLOW_PREFIX}:{key}"


async def resolve(raw: str, store: CallbackStore) -> Callback | None:
    """Inverse of :func:`encode_safe` — resolves overflow keys back to the original."""
    if raw.startswith(f"{OVERFLOW_PREFIX}:"):
        key = raw.split(":", 3)[3]
        payload = await store.get(key)
        if payload is None:
            return None
        return parse(payload)
    return parse(raw)
