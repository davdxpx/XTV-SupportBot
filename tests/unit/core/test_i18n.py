"""I18n translator tests."""

from __future__ import annotations

import pytest

from xtv_support.core.i18n import I18n


@pytest.fixture
def i18n() -> I18n:
    return I18n(
        locales={
            "en": {
                "meta": {"code": "en", "native_name": "English"},
                "user": {
                    "welcome": "Welcome, {name}!",
                    "ticket_created": "Ticket #{ticket_id} created",
                    "advanced": "Only in English",
                },
                "ticket": {
                    "count_one": "1 ticket",
                    "count_other": "{count} tickets",
                },
            },
            "de": {
                "meta": {"code": "de", "native_name": "Deutsch"},
                "user": {"welcome": "Willkommen, {name}!"},
            },
        },
        default_lang="en",
    )


def test_basic_lookup_with_placeholder(i18n: I18n) -> None:
    assert i18n.t("user.welcome", locale="de", name="Anna") == "Willkommen, Anna!"
    assert i18n.t("user.welcome", locale="en", name="Bob") == "Welcome, Bob!"


def test_falls_back_to_default_locale_when_key_missing(i18n: I18n) -> None:
    # "user.advanced" is only in en; request de.
    assert i18n.t("user.advanced", locale="de") == "Only in English"


def test_unknown_key_returns_key_itself(i18n: I18n) -> None:
    assert i18n.t("user.totally_unknown", locale="en") == "user.totally_unknown"


def test_unknown_locale_falls_back_to_default(i18n: I18n) -> None:
    assert i18n.t("user.welcome", locale="ja", name="X") == "Welcome, X!"


def test_plural_one(i18n: I18n) -> None:
    assert i18n.t("ticket.count", locale="en", count=1) == "1 ticket"


def test_plural_other(i18n: I18n) -> None:
    assert i18n.t("ticket.count", locale="en", count=7) == "7 tickets"


def test_plural_zero_uses_other(i18n: I18n) -> None:
    assert i18n.t("ticket.count", locale="en", count=0) == "0 tickets"


def test_plural_without_count_kwarg_uses_base_key(i18n: I18n) -> None:
    # no _base key defined, so we get the key back
    assert i18n.t("ticket.count", locale="en") == "ticket.count"


def test_missing_placeholder_returns_raw_template(i18n: I18n) -> None:
    # Forgot `name=...` — must not raise.
    assert i18n.t("user.welcome", locale="en") == "Welcome, {name}!"


def test_has_reports_presence(i18n: I18n) -> None:
    assert i18n.has("user.welcome", locale="de") is True
    assert i18n.has("user.advanced", locale="de") is True  # via fallback
    assert i18n.has("does.not.exist", locale="en") is False


def test_supported_and_default(i18n: I18n) -> None:
    assert i18n.supported() == ["de", "en"]
    assert i18n.default_lang == "en"


def test_none_locale_uses_default(i18n: I18n) -> None:
    assert i18n.t("user.welcome", name="Eve") == "Welcome, Eve!"


def test_dotted_key_can_return_non_string_silently() -> None:
    # If a caller asks for a map node (not a leaf), we should not crash —
    # we treat it as missing and return the key.
    i = I18n({"en": {"user": {"sub": {"leaf": "x"}}}}, default_lang="en")
    assert i.t("user.sub", locale="en") == "user.sub"
    assert i.t("user.sub.leaf", locale="en") == "x"
