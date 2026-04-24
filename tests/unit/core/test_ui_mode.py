"""Tests for the UI-mode switch helpers."""

from __future__ import annotations

import pytest

from xtv_support.core.ui_mode import (
    UIMode,
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
