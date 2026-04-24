"""Tests for the UI-mode switch helpers."""

from __future__ import annotations

import pytest

from xtv_support.core.ui_mode import (
    UIMode,
    client_supports_webapp,
    resolve_mode_for_user,
    resolved_mode,
    should_render_callbacks,
    should_use_webapp,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("chat", UIMode.CHAT),
        ("webapp", UIMode.WEBAPP),
        ("hybrid", UIMode.HYBRID),
        ("CHAT", UIMode.CHAT),
        ("  Hybrid  ", UIMode.HYBRID),
        ("bogus", UIMode.CHAT),
        (None, UIMode.CHAT),
        ("", UIMode.CHAT),
    ],
)
def test_parse_is_tolerant(raw: str | None, expected: UIMode) -> None:
    assert UIMode.parse(raw) is expected


def test_user_pref_beats_global() -> None:
    assert resolved_mode(global_mode="chat", user_pref="webapp") is UIMode.WEBAPP
    assert resolved_mode(global_mode=UIMode.WEBAPP, user_pref="chat") is UIMode.CHAT


def test_user_pref_none_falls_back_to_global() -> None:
    assert resolved_mode(global_mode="hybrid", user_pref=None) is UIMode.HYBRID


def test_should_use_webapp() -> None:
    assert should_use_webapp(UIMode.WEBAPP)
    assert should_use_webapp(UIMode.HYBRID)
    assert not should_use_webapp(UIMode.CHAT)


def test_should_render_callbacks() -> None:
    assert should_render_callbacks(UIMode.CHAT)
    assert should_render_callbacks(UIMode.HYBRID)
    assert not should_render_callbacks(UIMode.WEBAPP)


# ----------------------------------------------------------------------
# Client-version detection
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "version, expected",
    [
        ("9.4.2", True),
        ("6.0", True),
        ("6.0.1", True),
        ("5.9", False),
        ("4.12.0", False),
        ("", True),  # unparseable → optimistic
        (None, True),  # missing → optimistic
        ("Telegram 10.1 (iOS)", True),  # leading text, digits still parsed
    ],
)
def test_client_supports_webapp(version: str | None, expected: bool) -> None:
    assert client_supports_webapp(version) is expected


# ----------------------------------------------------------------------
# resolve_mode_for_user (async) — fake Mongo interface
# ----------------------------------------------------------------------
class _FakeUsersCollection:
    def __init__(self, doc: dict | None) -> None:
        self._doc = doc

    async def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        del query, projection
        return self._doc


class _FakeDB:
    def __init__(self, user_doc: dict | None = None) -> None:
        self.users = _FakeUsersCollection(user_doc)


async def test_resolve_uses_user_pref_over_global() -> None:
    db = _FakeDB(user_doc={"ui_pref": "webapp"})
    mode = await resolve_mode_for_user(
        db,  # type: ignore[arg-type]
        user_id=1,
        global_mode="chat",
        webapp_url="https://x.example",
    )
    assert mode is UIMode.WEBAPP


async def test_resolve_falls_back_when_url_missing() -> None:
    """Pref says webapp but no WEBAPP_URL → degrade to chat silently."""
    db = _FakeDB(user_doc={"ui_pref": "webapp"})
    mode = await resolve_mode_for_user(
        db,  # type: ignore[arg-type]
        user_id=1,
        global_mode="webapp",
        webapp_url="",
    )
    assert mode is UIMode.CHAT


async def test_resolve_falls_back_on_old_client() -> None:
    """Even in hybrid mode, an old Telegram client gets chat-only."""
    db = _FakeDB(user_doc=None)
    mode = await resolve_mode_for_user(
        db,  # type: ignore[arg-type]
        user_id=1,
        global_mode="hybrid",
        webapp_url="https://x.example",
        client_version="5.9",
    )
    assert mode is UIMode.CHAT


async def test_resolve_passes_through_when_clean() -> None:
    db = _FakeDB(user_doc=None)
    mode = await resolve_mode_for_user(
        db,  # type: ignore[arg-type]
        user_id=1,
        global_mode="hybrid",
        webapp_url="https://x.example",
        client_version="10.1",
    )
    assert mode is UIMode.HYBRID


async def test_resolve_tolerates_mongo_errors() -> None:
    """Mongo hiccup → fall through to global default, don't crash."""

    class _BrokenUsers:
        async def find_one(self, *args, **kwargs):
            raise RuntimeError("boom")

    class _BrokenDB:
        users = _BrokenUsers()

    mode = await resolve_mode_for_user(
        _BrokenDB(),  # type: ignore[arg-type]
        user_id=1,
        global_mode="webapp",
        webapp_url="https://x.example",
    )
    assert mode is UIMode.WEBAPP
