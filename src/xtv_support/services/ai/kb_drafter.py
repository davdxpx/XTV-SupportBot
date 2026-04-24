"""Knowledge-base article drafter.

Given a solved ticket conversation, drafts a short KB article that an
admin can tweak and publish with ``/kb add``. Output is parsed into a
structured :class:`KbDraft` so the handler can pre-fill the ``/kb add``
form instead of asking the admin to split the response by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.services.ai import prompts
from xtv_support.services.ai.redaction import redact

log = get_logger("ai.kb_drafter")


@dataclass(frozen=True, slots=True)
class KbDraft:
    title: str
    tags: tuple[str, ...]
    body: str
    raw: str = ""
    ok: bool = False
    error: str | None = None


def parse(text: str) -> KbDraft:
    """Parse a ``Title:/Tags:/Body:`` response."""
    if not text:
        return KbDraft(title="", tags=(), body="", ok=False, error="empty")
    title = ""
    tags: list[str] = []
    body_lines: list[str] = []
    section = None
    for line in text.splitlines():
        m = re.match(r"\s*(title|tags|body)\s*:\s*(.*)$", line, re.IGNORECASE)
        if m:
            key = m.group(1).lower()
            value = m.group(2).strip()
            if key == "title":
                section = "title"
                title = value
            elif key == "tags":
                section = "tags"
                tags = [t.strip() for t in value.split(",") if t.strip()]
            elif key == "body":
                section = "body"
                if value:
                    body_lines.append(value)
        elif section == "body":
            body_lines.append(line)
        elif section == "title" and line.strip():
            # Continuation of a multi-line title — rare but tolerated.
            title = (title + " " + line.strip()).strip()

    body = "\n".join(body_lines).strip()
    ok = bool(title and body)
    return KbDraft(
        title=title,
        tags=tuple(tags),
        body=body,
        raw=text,
        ok=ok,
        error=None if ok else "incomplete",
    )


async def draft_article(
    client: AIClient,
    *,
    conversation_text: str,
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> KbDraft:
    clean = redact(conversation_text, enabled=client.config.redact_pii).redacted
    messages = prompts.build_kb_drafter_prompt(clean)
    result = await client.complete(
        feature="kb_drafter",
        messages=messages,
        model=client.config.default_model,  # quality matters more than speed here
        user_id=user_id,
        ticket_id=ticket_id,
    )
    if not result.ok:
        return KbDraft(
            title="",
            tags=(),
            body="",
            ok=False,
            error=result.error or "ai_call_failed",
        )
    parsed = parse(result.text)
    log.info(
        "ai.kb_drafter.ok" if parsed.ok else "ai.kb_drafter.partial",
        ticket_id=ticket_id,
        title_len=len(parsed.title),
        body_len=len(parsed.body),
        tags=list(parsed.tags),
    )
    return parsed
