"""Sentiment-classification service.

Wraps a single-label classifier over the ``TicketSentiment`` enum.
The prompt asks the model to return exactly one of ``positive /
neutral / negative / urgent``; we parse leniently (case-insensitive,
ignore stray punctuation) and fall back to NEUTRAL when the model
returns something unexpected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from xtv_support.core.logger import get_logger
from xtv_support.domain.enums import TicketSentiment
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.services.ai import prompts
from xtv_support.services.ai.redaction import redact

log = get_logger("ai.sentiment")

_LABEL_RE = re.compile(r"[a-zA-Z]+")


@dataclass(frozen=True, slots=True)
class SentimentResult:
    sentiment: TicketSentiment
    confident: bool  # False when we had to fall back
    raw: str = ""
    error: str | None = None


def parse(text: str) -> SentimentResult:
    """Extract the first word and map it to a :class:`TicketSentiment`."""
    if not text:
        return SentimentResult(sentiment=TicketSentiment.NEUTRAL, confident=False, error="empty")
    match = _LABEL_RE.search(text)
    if not match:
        return SentimentResult(
            sentiment=TicketSentiment.NEUTRAL, confident=False, raw=text, error="no_label"
        )
    label = match.group(0).lower()
    try:
        return SentimentResult(sentiment=TicketSentiment(label), confident=True, raw=text)
    except ValueError:
        return SentimentResult(
            sentiment=TicketSentiment.NEUTRAL, confident=False, raw=text, error="unknown_label"
        )


async def classify(
    client: AIClient,
    *,
    user_text: str,
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> SentimentResult:
    clean = redact(user_text, enabled=client.config.redact_pii).redacted
    messages = prompts.build_sentiment_prompt(clean)
    result = await client.complete(
        feature="sentiment",
        messages=messages,
        model=client.config.fast_model,
        max_tokens=8,  # single word, tiny cap
        temperature=0.0,  # no creativity wanted here
        user_id=user_id,
        ticket_id=ticket_id,
    )
    if not result.ok:
        return SentimentResult(
            sentiment=TicketSentiment.NEUTRAL,
            confident=False,
            error=result.error or "ai_call_failed",
        )
    parsed = parse(result.text)
    log.info(
        "ai.sentiment",
        ticket_id=ticket_id,
        label=parsed.sentiment.value,
        confident=parsed.confident,
    )
    return parsed
