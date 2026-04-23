"""Ticket-summary service.

Parses the AI's three-section output (``Problem: ... / Resolution: ...
/ Tags: ...``) into a typed :class:`TicketSummary` so the history
record can store structured fields instead of a blob.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.ai.client import AIClient, AIResult
from xtv_support.services.ai import prompts
from xtv_support.services.ai.redaction import redact

log = get_logger("ai.summary")

_SECTION_RE = re.compile(
    r"^\s*(?:problem|resolution|tags)\s*:", re.IGNORECASE | re.MULTILINE
)


@dataclass(frozen=True, slots=True)
class TicketSummary:
    """Structured summary payload."""

    problem: str = ""
    resolution: str = ""
    tags: tuple[str, ...] = ()
    raw: str = ""               # full text from the model
    ok: bool = False            # mirrors AIResult.ok for convenience
    error: str | None = None


def parse(text: str) -> TicketSummary:
    """Extract the three sections from the model's raw response."""
    if not text:
        return TicketSummary(ok=False, error="empty")

    parts = {"problem": "", "resolution": "", "tags": ""}
    current = None
    for line in text.splitlines():
        m = re.match(r"\s*(problem|resolution|tags)\s*:\s*(.*)$", line, re.IGNORECASE)
        if m:
            current = m.group(1).lower()
            parts[current] = m.group(2).strip()
        elif current is not None and line.strip():
            parts[current] += (" " if parts[current] else "") + line.strip()

    tags = [t.strip() for t in parts["tags"].split(",") if t.strip()]
    return TicketSummary(
        problem=parts["problem"].strip(),
        resolution=parts["resolution"].strip(),
        tags=tuple(tags),
        raw=text,
        ok=bool(parts["problem"] and parts["resolution"]),
        error=None if (parts["problem"] and parts["resolution"]) else "incomplete",
    )


async def summarise(
    client: AIClient,
    *,
    conversation_text: str,
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> TicketSummary:
    """Run the summary prompt and parse the response."""
    clean = redact(conversation_text, enabled=client.config.redact_pii).redacted
    messages = prompts.build_summary_prompt(clean)
    result: AIResult = await client.complete(
        feature="summary",
        messages=messages,
        model=client.config.fast_model,   # cheaper model — summaries are short
        user_id=user_id,
        ticket_id=ticket_id,
    )
    if not result.ok:
        return TicketSummary(ok=False, error=result.error or "ai_call_failed")

    summary = parse(result.text)
    log.info(
        "ai.summary.ok" if summary.ok else "ai.summary.partial",
        ticket_id=ticket_id,
        problem_len=len(summary.problem),
        resolution_len=len(summary.resolution),
        tags=list(summary.tags),
    )
    return summary
