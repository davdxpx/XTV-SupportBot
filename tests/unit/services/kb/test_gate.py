"""KB gate tests — evaluate() is pure (modulo bus publish)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from xtv_support.domain.events import KbArticleShown
from xtv_support.domain.models.kb import KbArticle
from xtv_support.services.kb import gate as kb_gate


def _article(slug: str, title: str = "T", body: str = "B") -> KbArticle:
    return KbArticle(id=slug, slug=slug, title=title, body=body, lang="en")


# ----------------------------------------------------------------------
# GateResult.triggered
# ----------------------------------------------------------------------
def test_gate_result_empty_is_not_triggered() -> None:
    assert kb_gate.GateResult().triggered is False


def test_gate_result_with_suggestions_triggers() -> None:
    r = kb_gate.GateResult(suggestions=(_article("x"),))
    assert r.triggered is True


# ----------------------------------------------------------------------
# evaluate()
# ----------------------------------------------------------------------
async def test_no_hits_returns_empty_and_no_event(monkeypatch) -> None:
    from xtv_support.services.kb import gate

    monkeypatch.setattr(gate, "search", AsyncMock(return_value=[]), raising=True)
    bus = SimpleNamespace(publish=AsyncMock())

    result = await kb_gate.evaluate(SimpleNamespace(), bus, user_id=1, query="random nonsense")
    assert not result.triggered
    bus.publish.assert_not_awaited()


async def test_hits_publish_article_shown_per_suggestion(monkeypatch) -> None:
    from xtv_support.services.kb import gate

    articles = [_article("a"), _article("b"), _article("c")]
    monkeypatch.setattr(gate, "search", AsyncMock(return_value=articles), raising=True)
    bus = SimpleNamespace(publish=AsyncMock())

    result = await kb_gate.evaluate(
        SimpleNamespace(),
        bus,
        user_id=42,
        query="reset password please",
        lang="en",
    )
    assert result.triggered
    assert tuple(a.slug for a in result.suggestions) == ("a", "b", "c")

    assert bus.publish.await_count == 3
    events = [c.args[0] for c in bus.publish.await_args_list]
    assert all(isinstance(e, KbArticleShown) for e in events)
    assert [e.rank for e in events] == [0, 1, 2]
    assert events[0].user_id == 42
    assert events[0].query == "reset password please"


async def test_evaluate_with_none_bus_still_returns_results(monkeypatch) -> None:
    from xtv_support.services.kb import gate

    articles = [_article("x")]
    monkeypatch.setattr(gate, "search", AsyncMock(return_value=articles), raising=True)

    result = await kb_gate.evaluate(SimpleNamespace(), None, user_id=1, query="hello world")
    assert result.triggered and result.suggestions[0].slug == "x"


async def test_evaluate_respects_max_suggestions(monkeypatch) -> None:
    from xtv_support.services.kb import gate

    captured: dict = {}

    async def _search(*_a, **kw):
        captured.update(kw)
        return []

    monkeypatch.setattr(gate, "search", _search, raising=True)
    await kb_gate.evaluate(
        SimpleNamespace(),
        None,
        user_id=1,
        query="test query",
        lang="hi",
        default_lang="en",
        project_id="support",
        max_suggestions=5,
    )
    assert captured["limit"] == 5
    assert captured["lang"] == "hi"
    assert captured["default_lang"] == "en"
    assert captured["project_id"] == "support"
