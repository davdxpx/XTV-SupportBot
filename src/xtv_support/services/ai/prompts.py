"""Prompt builders for the AI feature services.

Each function returns a ``list[dict]`` in the OpenAI-style
``messages`` format that LiteLLM accepts regardless of the target
provider. Keeping the prompts here (instead of inline in each service)
makes them:

* reviewable in one place,
* swappable for A/B experiments,
* cacheable — identical system prompts get a hit on Anthropic's
  prompt-caching if the provider is Anthropic.
"""
from __future__ import annotations

from typing import Sequence

# ----------------------------------------------------------------------
# System prompts — stable, cacheable.
# ----------------------------------------------------------------------
SYSTEM_DRAFT_REPLY = (
    "You are an expert customer-support agent drafting a reply an "
    "agent can send to a user. Write in the same language the user "
    "used. Be concise, helpful, and never invent facts. If the user's "
    "request needs information you don't have, say so and suggest "
    "what the agent should ask for. Sign-off with 'Kind regards' "
    "only. Do NOT include salutations or template placeholders."
)

SYSTEM_SUMMARY = (
    "You are an internal analyst summarising a closed support "
    "conversation for the team's records. Produce exactly three "
    "sections in plain text:\n"
    "1. Problem: one sentence.\n"
    "2. Resolution: one sentence.\n"
    "3. Tags: up to five short tags, comma-separated.\n"
    "No markdown, no headings, no fluff."
)

SYSTEM_SENTIMENT = (
    "Classify the overall sentiment of the user's message. Respond "
    "with ONLY one lowercase word from this set: "
    "positive, neutral, negative, urgent."
)

SYSTEM_ROUTING = (
    "You are a ticket-routing assistant. Given the user's first "
    "message and the list of available teams (one per line, 'slug: "
    "description'), pick the best team. Respond with ONLY the slug. "
    "If no team fits, respond with 'general'."
)

SYSTEM_TRANSLATE = (
    "Translate the user's message into {target_lang}. Preserve tone "
    "and formatting. If the message is already in {target_lang}, "
    "return it unchanged. Output ONLY the translation, nothing else."
)

SYSTEM_KB_DRAFTER = (
    "You are a technical writer drafting a short knowledge-base "
    "article from a solved support conversation. Use this format:\n"
    "Title: <short title>\n"
    "Tags: <comma-separated tags>\n"
    "Body:\n<body in 1-3 short paragraphs>\n"
    "Do not fabricate product names or features that weren't in the "
    "conversation."
)


# ----------------------------------------------------------------------
# Builders
# ----------------------------------------------------------------------
def build_draft_prompt(
    *, conversation: Sequence[dict[str, str]], pending_user_message: str
) -> list[dict[str, str]]:
    """Build messages for the reply-draft feature.

    ``conversation`` is a list of ``{role, content}`` entries from the
    ticket history (oldest first). ``pending_user_message`` is the
    latest user-sent text the agent hasn't replied to yet.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_DRAFT_REPLY},
    ]
    messages.extend(dict(m) for m in conversation)
    messages.append({"role": "user", "content": pending_user_message})
    return messages


def build_summary_prompt(conversation_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_SUMMARY},
        {"role": "user", "content": conversation_text},
    ]


def build_sentiment_prompt(user_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_SENTIMENT},
        {"role": "user", "content": user_text},
    ]


def build_routing_prompt(
    *, user_text: str, teams: Sequence[tuple[str, str]]
) -> list[dict[str, str]]:
    teams_block = "\n".join(f"{slug}: {descr}" for slug, descr in teams)
    return [
        {"role": "system", "content": SYSTEM_ROUTING},
        {
            "role": "user",
            "content": f"Teams:\n{teams_block}\n\nUser message:\n{user_text}",
        },
    ]


def build_translate_prompt(
    *, source_text: str, target_lang: str
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": SYSTEM_TRANSLATE.format(target_lang=target_lang),
        },
        {"role": "user", "content": source_text},
    ]


def build_kb_drafter_prompt(conversation_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_KB_DRAFTER},
        {"role": "user", "content": conversation_text},
    ]
