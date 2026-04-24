from __future__ import annotations

import asyncio

from xtv_support.core.callback_v2 import (
    MAX_CALLBACK_BYTES,
    InMemoryCallbackStore,
    build,
    encode_safe,
    parse,
    resolve,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def test_build_encode_parse_roundtrip() -> None:
    cb = build("inbox", "bulk", "close", "42")
    raw = cb.encode()
    assert raw == "cb:v2:inbox:bulk:close:42"
    parsed = parse(raw)
    assert parsed is not None
    assert parsed.namespace == "inbox"
    assert parsed.action == "bulk"
    assert parsed.args == ("close", "42")


def test_parse_rejects_foreign_prefix() -> None:
    assert parse("admin:project|abc") is None
    assert parse("") is None
    assert parse("cb:v2:only") is None  # too short


def test_encode_safe_inline_when_short() -> None:
    store = InMemoryCallbackStore()
    cb = build("x", "y", "1")
    raw = _run(encode_safe(cb, store))
    assert raw == cb.encode()
    assert len(raw.encode()) <= MAX_CALLBACK_BYTES


def test_encode_safe_overflow_spills_to_store() -> None:
    store = InMemoryCallbackStore()
    cb = build("inbox", "bulk", "a" * 200)
    raw = _run(encode_safe(cb, store))
    assert raw.startswith("cb:v2:ov:")
    assert len(raw.encode()) <= MAX_CALLBACK_BYTES
    back = _run(resolve(raw, store))
    assert back == cb


def test_store_lru_eviction() -> None:
    store = InMemoryCallbackStore(max_entries=2)

    async def _fill() -> tuple[str, str]:
        k1 = await store.put("one")
        k2 = await store.put("two")
        await store.put("three")
        return k1, k2

    k1, k2 = _run(_fill())
    assert _run(store.get(k1)) is None
    assert _run(store.get(k2)) == "two"
