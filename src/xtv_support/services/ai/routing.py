"""Smart-routing service — suggest a team for a freshly-created ticket.

The pure routing engine in :mod:`xtv_support.services.teams.routing`
picks a team from *declarative* rules. This service is the fuzzy
counterpart: it asks the AI to pick from free-text team descriptions,
useful when an operator's queue rules haven't been written yet or the
ticket doesn't match any of them.

The output is always **a slug that exists in the provided team list**
— we never trust the AI's raw response to be valid. When the returned
slug is unknown we fall back to ``general`` and mark the result as
non-confident.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.services.ai import prompts
from xtv_support.services.ai.redaction import redact

log = get_logger("ai.routing")

_FALLBACK = "general"
_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")


@dataclass(frozen=True, slots=True)
class RoutingSuggestion:
    team_id: str
    confident: bool
    raw: str = ""
    error: str | None = None


def parse(text: str, known_slugs: Iterable[str]) -> RoutingSuggestion:
    known = {s.lower() for s in known_slugs}
    if not text:
        return RoutingSuggestion(
            team_id=_FALLBACK, confident=False, error="empty"
        )
    # First slug-looking token wins.
    match = _SLUG_RE.search(text.lower())
    candidate = match.group(0) if match else ""
    if candidate and candidate in known:
        return RoutingSuggestion(team_id=candidate, confident=True, raw=text)
    if candidate == _FALLBACK:
        return RoutingSuggestion(
            team_id=_FALLBACK, confident=False, raw=text, error="ai_chose_fallback"
        )
    return RoutingSuggestion(
        team_id=_FALLBACK, confident=False, raw=text, error="unknown_slug"
    )


async def suggest(
    client: AIClient,
    *,
    user_text: str,
    teams: list[tuple[str, str]],   # [(slug, description), ...]
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> RoutingSuggestion:
    if not teams:
        return RoutingSuggestion(
            team_id=_FALLBACK, confident=False, error="no_teams_given"
        )
    clean = redact(user_text, enabled=client.config.redact_pii).redacted
    messages = prompts.build_routing_prompt(user_text=clean, teams=teams)
    result = await client.complete(
        feature="routing",
        messages=messages,
        model=client.config.fast_model,
        max_tokens=32,
        temperature=0.0,
        user_id=user_id,
        ticket_id=ticket_id,
    )
    if not result.ok:
        return RoutingSuggestion(
            team_id=_FALLBACK,
            confident=False,
            error=result.error or "ai_call_failed",
        )
    parsed = parse(result.text, [slug for slug, _ in teams])
    log.info(
        "ai.routing",
        ticket_id=ticket_id,
        suggested=parsed.team_id,
        confident=parsed.confident,
        error=parsed.error,
    )
    return parsed
