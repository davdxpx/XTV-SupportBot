"""Tests for the i18n locale picker.

The pyrofork glue in ``xtv_support.middlewares.i18n_mw`` is thin and
only wires the pure :func:`pick_locale` into ``@Client.on_message``; we
test the picker and the normaliser directly here since they carry every
non-trivial branch.
"""

from __future__ import annotations

import pytest

from xtv_support.core.i18n import normalise_lang_code, pick_locale


def test_normalise_strips_regional_suffix() -> None:
    assert normalise_lang_code("en-US") == "en"
    assert normalise_lang_code("HI") == "hi"
    assert normalise_lang_code("pt-BR") == "pt"


def test_normalise_handles_empty_and_none() -> None:
    assert normalise_lang_code("") is None
    assert normalise_lang_code(None) is None
    assert normalise_lang_code("   ") is None


SUPPORTED = ["en", "ru", "es", "hi", "bn"]


def test_preferred_wins_when_supported() -> None:
    out = pick_locale(
        preferred="ru",
        telegram_code="en-US",
        supported=SUPPORTED,
        default_lang="en",
    )
    assert out == "ru"


def test_telegram_used_when_no_preferred() -> None:
    out = pick_locale(
        preferred=None,
        telegram_code="hi-IN",
        supported=SUPPORTED,
        default_lang="en",
    )
    assert out == "hi"


def test_default_used_when_telegram_unsupported() -> None:
    out = pick_locale(
        preferred=None,
        telegram_code="de",
        supported=SUPPORTED,
        default_lang="en",
    )
    assert out == "en"


def test_default_used_when_no_inputs() -> None:
    out = pick_locale(
        preferred=None,
        telegram_code=None,
        supported=SUPPORTED,
        default_lang="en",
    )
    assert out == "en"


def test_preferred_unsupported_falls_through_to_telegram() -> None:
    out = pick_locale(
        preferred="klingon",
        telegram_code="ru",
        supported=SUPPORTED,
        default_lang="en",
    )
    assert out == "ru"


def test_preferred_empty_string_ignored() -> None:
    out = pick_locale(
        preferred="",
        telegram_code="ru",
        supported=SUPPORTED,
        default_lang="en",
    )
    assert out == "ru"


def test_telegram_with_region_normalised_and_matched() -> None:
    out = pick_locale(
        preferred=None,
        telegram_code="en-GB",
        supported=SUPPORTED,
        default_lang="hi",
    )
    assert out == "en"


@pytest.mark.parametrize("default", ["en", "hi", "ru"])
def test_default_applies_for_unknowns(default: str) -> None:
    out = pick_locale(
        preferred=None,
        telegram_code="unknown",
        supported=SUPPORTED,
        default_lang=default,
    )
    assert out == default
