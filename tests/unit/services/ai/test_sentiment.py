"""Sentiment classifier tests."""

from __future__ import annotations

import pytest

from xtv_support.domain.enums import TicketSentiment
from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.services.ai.sentiment import classify, parse


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("positive", TicketSentiment.POSITIVE),
        ("NEUTRAL", TicketSentiment.NEUTRAL),
        ("Negative.", TicketSentiment.NEGATIVE),
        ("urgent!", TicketSentiment.URGENT),
        ("  positive  ", TicketSentiment.POSITIVE),
    ],
)
def test_parse_valid_labels(raw: str, expected: TicketSentiment) -> None:
    result = parse(raw)
    assert result.sentiment is expected
    assert result.confident is True


def test_parse_empty_falls_back_to_neutral() -> None:
    result = parse("")
    assert result.sentiment is TicketSentiment.NEUTRAL
    assert result.confident is False
    assert result.error == "empty"


def test_parse_unknown_label_falls_back() -> None:
    result = parse("apathy")
    assert result.sentiment is TicketSentiment.NEUTRAL
    assert result.confident is False
    assert result.error == "unknown_label"


def test_parse_no_word_character() -> None:
    result = parse("...!!!")
    assert result.sentiment is TicketSentiment.NEUTRAL
    assert result.confident is False
    assert result.error == "no_label"


async def test_classify_happy_path() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [{"message": {"content": "urgent"}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 1},
        }

    client._call_litellm = fake
    r = await classify(client, user_text="EVERYTHING IS BROKEN")
    assert r.sentiment is TicketSentiment.URGENT
    assert r.confident


async def test_classify_disabled() -> None:
    client = AIClient(AIConfig(enabled=False))
    r = await classify(client, user_text="hello")
    assert r.sentiment is TicketSentiment.NEUTRAL
    assert not r.confident
    assert r.error == "ai_disabled"
