"""Auto-translation service.

Translates a source text into a target locale. Used by the
cross-locale bridge when the user and the agent don't share a
language. The underlying prompt explicitly tells the model to return
the input unchanged when it's already in the target language, so
monolingual teams don't pay a token bill on English-to-English
round-trips.
"""
from __future__ import annotations

from dataclasses import dataclass

from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.services.ai import prompts

log = get_logger("ai.translate")


@dataclass(frozen=True, slots=True)
class TranslationResult:
    translated: str
    same_as_source: bool         # True when the model returned the input verbatim
    ok: bool
    error: str | None = None


async def translate(
    client: AIClient,
    *,
    source_text: str,
    target_lang: str,
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> TranslationResult:
    if not source_text.strip():
        return TranslationResult(translated="", same_as_source=True, ok=True)

    messages = prompts.build_translate_prompt(
        source_text=source_text, target_lang=target_lang
    )
    result = await client.complete(
        feature="translate",
        messages=messages,
        model=client.config.default_model,
        user_id=user_id,
        ticket_id=ticket_id,
    )
    if not result.ok:
        return TranslationResult(
            translated=source_text,
            same_as_source=True,
            ok=False,
            error=result.error or "ai_call_failed",
        )

    translated = result.text.strip()
    same = translated == source_text.strip()
    log.info(
        "ai.translate.ok",
        target_lang=target_lang,
        ticket_id=ticket_id,
        same_as_source=same,
    )
    return TranslationResult(
        translated=translated or source_text,
        same_as_source=same,
        ok=True,
    )
