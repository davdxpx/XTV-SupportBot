"""Reply-draft service tests."""

from __future__ import annotations

from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.services.ai.drafts import draft_reply


async def test_disabled_client_short_circuits() -> None:
    client = AIClient(AIConfig(enabled=False))
    result = await draft_reply(
        client,
        conversation=[],
        pending_user_message="hi",
    )
    assert result.ok is False
    assert result.error == "ai_disabled"


async def test_redacts_pii_before_sending() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=True))

    captured_messages: list[dict] = []

    async def fake(**kw):
        captured_messages.extend(kw["messages"])
        return {
            "choices": [{"message": {"content": "Hello."}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        }

    client._call_litellm = fake

    await draft_reply(
        client,
        conversation=[
            {"role": "user", "content": "write to me at foo@example.com"},
        ],
        pending_user_message="my card is 4111 1111 1111 1111",
    )

    # User-message content reached the provider but with PII removed.
    user_contents = [m["content"] for m in captured_messages if m["role"] == "user"]
    joined = "\n".join(user_contents)
    assert "foo@example.com" not in joined
    assert "4111 1111 1111 1111" not in joined
    assert "[REDACTED:credit_card]" in joined
    assert "[email#" in joined


async def test_returns_happy_result() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [{"message": {"content": "Draft reply."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            "_cost_usd": 0.00001,
        }

    client._call_litellm = fake
    result = await draft_reply(
        client,
        conversation=[{"role": "user", "content": "help"}],
        pending_user_message="please",
        ticket_id="t42",
    )
    assert result.ok
    assert result.text == "Draft reply."
    assert result.feature == "drafts"
