"""Macros service tests — render() + consume()."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from xtv_support.domain.events import MacroUsed
from xtv_support.domain.models.macro import Macro
from xtv_support.services.macros.service import consume, render


def _macro(**kw) -> Macro:
    defaults = dict(id="m1", name="greet", body="Hi", team_id=None)
    defaults.update(kw)
    return Macro(**defaults)


# ----------------------------------------------------------------------
# render()
# ----------------------------------------------------------------------
def test_render_substitutes_named_placeholders() -> None:
    m = _macro(body="Hello {user_name}, ticket #{ticket_id} received.")
    out = render(m, user_name="Anna", ticket_id="42")
    assert out == "Hello Anna, ticket #42 received."


def test_render_returns_raw_when_placeholder_missing() -> None:
    m = _macro(body="Hello {user_name}!")
    out = render(m, other_key="nope")
    assert out == "Hello {user_name}!"


def test_render_handles_body_without_placeholders() -> None:
    m = _macro(body="Thanks for reaching out.")
    assert render(m, ticket_id="42") == "Thanks for reaching out."


def test_render_ignores_extra_context() -> None:
    m = _macro(body="Ticket {ticket_id}")
    assert render(m, ticket_id="x", user_name="Bob") == "Ticket x"


# ----------------------------------------------------------------------
# consume()
# ----------------------------------------------------------------------
async def test_consume_bumps_counter_and_publishes_event(monkeypatch) -> None:
    from xtv_support.infrastructure.db import macros as macros_repo

    inc = AsyncMock()
    monkeypatch.setattr(macros_repo, "increment_usage", inc, raising=True)

    bus = SimpleNamespace(publish=AsyncMock())
    db = SimpleNamespace()
    macro = _macro(team_id="support")
    await consume(db, bus, macro=macro, ticket_id="t42", actor_id=99)

    inc.assert_awaited_once_with(db, "m1")
    bus.publish.assert_awaited_once()
    event = bus.publish.await_args.args[0]
    assert isinstance(event, MacroUsed)
    assert event.macro_id == "m1"
    assert event.macro_name == "greet"
    assert event.ticket_id == "t42"
    assert event.actor_id == 99
    assert event.team_id == "support"


async def test_consume_swallows_counter_errors(monkeypatch) -> None:
    from xtv_support.infrastructure.db import macros as macros_repo

    async def _boom(*_a, **_k):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(macros_repo, "increment_usage", _boom, raising=True)
    bus = SimpleNamespace(publish=AsyncMock())

    # Must not raise; event still fires.
    await consume(
        SimpleNamespace(),
        bus,
        macro=_macro(),
        ticket_id="t1",
        actor_id=1,
    )
    bus.publish.assert_awaited_once()


# ----------------------------------------------------------------------
# Scope property
# ----------------------------------------------------------------------
def test_scope_global() -> None:
    assert _macro(team_id=None).scope == "global"


def test_scope_team() -> None:
    assert _macro(team_id="support").scope == "team:support"
