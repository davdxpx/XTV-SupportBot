"""KB service tests — search normalisation + locale fallback."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from xtv_support.domain.models.kb import KbArticle
from xtv_support.services.kb import service as kb_service
from xtv_support.services.kb.service import MIN_QUERY_LEN, normalise_query


def _article(slug: str = "x", lang: str = "en") -> KbArticle:
    return KbArticle(id=slug, slug=slug, title="T", body="B", lang=lang)


# ----------------------------------------------------------------------
# normalise_query()
# ----------------------------------------------------------------------
def test_normalise_trims_and_lowers() -> None:
    assert normalise_query("  Reset   password  ") == "reset password"


def test_normalise_empty_and_none_like() -> None:
    assert normalise_query("") == ""
    assert normalise_query("   ") == ""


# ----------------------------------------------------------------------
# search() — locale fallback
# ----------------------------------------------------------------------
async def test_too_short_query_returns_empty(monkeypatch) -> None:
    from xtv_support.infrastructure.db import kb as kb_repo

    called = AsyncMock()
    monkeypatch.setattr(kb_repo, "search", called, raising=True)

    out = await kb_service.search(SimpleNamespace(), "a")
    assert out == []
    called.assert_not_awaited()


async def test_search_hits_requested_locale_first(monkeypatch) -> None:
    from xtv_support.infrastructure.db import kb as kb_repo

    mock = AsyncMock()
    calls: list[tuple[str, dict]] = []

    async def side_effect(db, query, *, lang=None, project_id=None, limit=5):
        calls.append((query, {"lang": lang}))
        if lang == "hi":
            return [_article("a", "hi")]
        return []

    mock.side_effect = side_effect
    monkeypatch.setattr(kb_repo, "search", mock, raising=True)

    out = await kb_service.search(
        SimpleNamespace(), "reset password", lang="hi", default_lang="en"
    )
    assert len(out) == 1 and out[0].lang == "hi"
    # First try: hi
    assert calls[0][1]["lang"] == "hi"


async def test_search_falls_back_to_default_locale(monkeypatch) -> None:
    from xtv_support.infrastructure.db import kb as kb_repo

    async def side_effect(db, query, *, lang=None, project_id=None, limit=5):
        if lang == "hi":
            return []
        if lang == "en":
            return [_article("a", "en")]
        return []

    mock = AsyncMock(side_effect=side_effect)
    monkeypatch.setattr(kb_repo, "search", mock, raising=True)

    out = await kb_service.search(SimpleNamespace(), "password", lang="hi")
    assert len(out) == 1 and out[0].lang == "en"
    # Two attempts (hi + en) before the cross-locale attempt.
    assert mock.await_count == 2


async def test_search_cross_locale_last_resort(monkeypatch) -> None:
    from xtv_support.infrastructure.db import kb as kb_repo

    async def side_effect(db, query, *, lang=None, project_id=None, limit=5):
        if lang is None:
            return [_article("x", "de")]
        return []

    mock = AsyncMock(side_effect=side_effect)
    monkeypatch.setattr(kb_repo, "search", mock, raising=True)

    out = await kb_service.search(SimpleNamespace(), "hallo", lang="hi")
    assert len(out) == 1
    # Three calls: hi, en, None
    assert mock.await_count == 3


# ----------------------------------------------------------------------
# Locale-chain dedup
# ----------------------------------------------------------------------
def test_locale_fallback_dedups() -> None:
    # Same lang + default_lang -> chain has only one entry.
    chain = kb_service._locale_fallback("en", "en")
    assert chain == ["en"]


def test_locale_fallback_none_lang_uses_default_only() -> None:
    chain = kb_service._locale_fallback(None, "en")
    assert chain == ["en"]


def test_min_query_len_constant() -> None:
    assert MIN_QUERY_LEN == 3


# ----------------------------------------------------------------------
# KbArticle model
# ----------------------------------------------------------------------
def test_helpfulness_zero_when_no_feedback() -> None:
    a = KbArticle(id="x", slug="x", title="T", body="B")
    assert a.helpfulness == 0.0


def test_helpfulness_ratio() -> None:
    a = KbArticle(id="x", slug="x", title="T", body="B", helpful=7, not_helpful=3)
    assert a.helpfulness == 0.7


def test_helpfulness_all_unhelpful() -> None:
    a = KbArticle(id="x", slug="x", title="T", body="B", helpful=0, not_helpful=5)
    assert a.helpfulness == 0.0
