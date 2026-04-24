"""AskAndConfirm primitive — registry + state extraction."""

from __future__ import annotations

import pytest

from xtv_support.ui.primitives.ask_and_confirm import (
    HANDLERS,
    STATE_PREFIX,
    AkcState,
    extract,
    register,
    resolve,
)


def teardown_function() -> None:
    HANDLERS.clear()


def test_state_prefix_is_akc() -> None:
    assert STATE_PREFIX == "akc:"


def test_register_and_resolve_roundtrip() -> None:
    async def _h(ctx, client, user_id, text, args) -> None:
        return None

    register("teams:new:slug", _h)
    assert resolve("teams:new:slug") is _h


def test_register_rejects_empty_context() -> None:
    async def _h(ctx, client, user_id, text, args) -> None:
        return None

    with pytest.raises(ValueError):
        register("", _h)


def test_extract_returns_none_when_state_missing() -> None:
    assert extract(None) is None
    assert extract({}) is None
    assert extract({"data": {}}) is None


def test_extract_reads_data_bag() -> None:
    state_doc = {
        "state": "akc:teams:new:slug",
        "data": {
            "akc_context": "teams:new:slug",
            "akc_args": {"name": "Billing"},
            "akc_prompt_chat": 42,
            "akc_prompt_msg": 7,
        },
    }
    got = extract(state_doc)
    assert isinstance(got, AkcState)
    assert got.context == "teams:new:slug"
    assert got.args == {"name": "Billing"}
    assert got.prompt_chat_id == 42
    assert got.prompt_msg_id == 7


def test_extract_rejects_partial_state() -> None:
    # prompt_msg missing → unusable
    state_doc = {
        "state": "akc:x",
        "data": {"akc_context": "x", "akc_prompt_chat": 1},
    }
    assert extract(state_doc) is None
