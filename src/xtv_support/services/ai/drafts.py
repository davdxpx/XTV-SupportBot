"""Reply-draft service.

Given a ticket's conversation so far + the user's pending message,
produce a drafted reply the agent can edit and send. Never fails
loudly — returns an :class:`AIResult` with ``ok=False`` when the
client is disabled or the provider errored, and the calling plugin
silently skips the feature.
"""
from __future__ import annotations

from typing import Sequence

from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.ai.client import AIClient, AIResult
from xtv_support.services.ai import prompts
from xtv_support.services.ai.redaction import redact

log = get_logger("ai.drafts")


async def draft_reply(
    client: AIClient,
    *,
    conversation: Sequence[dict[str, str]],
    pending_user_message: str,
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> AIResult:
    """Draft a reply the agent can polish before sending.

    Redacts PII from both the pending message and each entry in
    ``conversation`` before building the prompt, so the upstream
    provider never sees raw credit cards / SSNs / API keys.
    """
    redact_pii = client.config.redact_pii
    scrubbed_convo: list[dict[str, str]] = []
    for entry in conversation:
        content = entry.get("content", "")
        clean = redact(content, enabled=redact_pii).redacted
        scrubbed_convo.append(
            {
                "role": str(entry.get("role", "user")),
                "content": clean,
            }
        )
    pending_clean = redact(pending_user_message, enabled=redact_pii).redacted

    messages = prompts.build_draft_prompt(
        conversation=scrubbed_convo,
        pending_user_message=pending_clean,
    )
    result = await client.complete(
        feature="drafts",
        messages=messages,
        model=client.config.default_model,
        user_id=user_id,
        ticket_id=ticket_id,
    )
    if result.ok:
        log.info(
            "ai.drafts.ok",
            ticket_id=ticket_id,
            tokens=result.prompt_tokens + result.completion_tokens,
            cost=result.cost_usd,
        )
    return result
