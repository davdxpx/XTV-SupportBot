"""Smart-routing tests."""

from __future__ import annotations

import pytest

from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.services.ai.routing import parse, suggest

KNOWN = ["billing", "support", "vip"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("billing", "billing"),
        ("support", "support"),
        ("VIP", "vip"),  # parser lowers
        (" billing ", "billing"),
    ],
)
def test_parse_known_slug(raw: str, expected: str) -> None:
    r = parse(raw, KNOWN)
    assert r.team_id == expected
    assert r.confident


def test_parse_fallback_when_ai_says_general() -> None:
    r = parse("general", KNOWN)
    assert r.team_id == "general"
    assert not r.confident
    assert r.error == "ai_chose_fallback"


def test_parse_unknown_slug_maps_to_general() -> None:
    r = parse("unicorn_team", KNOWN)
    assert r.team_id == "general"
    assert not r.confident
    assert r.error == "unknown_slug"


def test_parse_empty_input() -> None:
    r = parse("", KNOWN)
    assert r.team_id == "general"
    assert r.error == "empty"


def test_parse_extracts_first_slug_token() -> None:
    r = parse("I think billing is best", KNOWN)
    # "i" is not a known slug; it returns general with unknown_slug.
    assert r.team_id == "general"
    # Confirm the regex picked up a token — not all are valid slugs.
    assert r.error == "unknown_slug"


async def test_suggest_with_empty_teams_returns_fallback() -> None:
    client = AIClient(AIConfig(enabled=True))
    r = await suggest(client, user_text="help", teams=[])
    assert r.team_id == "general"
    assert r.error == "no_teams_given"


async def test_suggest_happy_path_picks_slug() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [{"message": {"content": "billing"}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 1},
        }

    client._call_litellm = fake
    r = await suggest(
        client,
        user_text="I got double-charged",
        teams=[("billing", "Invoices"), ("support", "General")],
    )
    assert r.team_id == "billing"
    assert r.confident


async def test_suggest_disabled_returns_fallback() -> None:
    client = AIClient(AIConfig(enabled=False))
    r = await suggest(
        client,
        user_text="help",
        teams=[("billing", "Invoices")],
    )
    assert r.team_id == "general"
    assert not r.confident
    assert r.error == "ai_disabled"
