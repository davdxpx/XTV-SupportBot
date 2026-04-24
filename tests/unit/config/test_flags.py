"""FeatureFlags unit tests."""

from __future__ import annotations

import pytest

from xtv_support.config.flags import FeatureFlags


def test_defaults_match_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    # Scrub every FEATURE_* env var so we see pristine defaults.
    for key in list(__import__("os").environ):
        if key.startswith("FEATURE_"):
            monkeypatch.delenv(key, raising=False)

    f = FeatureFlags(_env_file=None)  # type: ignore[call-arg]
    # Default-off set
    assert f.AI_DRAFTS is False
    assert f.AI_SUMMARY is False
    assert f.CSAT is False
    assert f.START_CAPTCHA is False
    assert f.WEBHOOKS_OUT is False
    # Default-on set
    assert f.LINK_SCANNER is True


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
    ],
)
def test_env_var_parses_booleans(monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool) -> None:
    monkeypatch.setenv("FEATURE_AI_DRAFTS", raw)
    f = FeatureFlags(_env_file=None)  # type: ignore[call-arg]
    assert f.AI_DRAFTS is expected


def test_is_enabled_helper_handles_case_and_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_CSAT", "true")
    f = FeatureFlags(_env_file=None)  # type: ignore[call-arg]
    assert f.is_enabled("csat") is True
    assert f.is_enabled("CSAT") is True
    assert f.is_enabled("ai_drafts") is False
    assert f.is_enabled("does_not_exist") is False


def test_extra_env_vars_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_SOMETHING_NEW_AND_UNKNOWN", "true")
    # Should not raise.
    FeatureFlags(_env_file=None)  # type: ignore[call-arg]
