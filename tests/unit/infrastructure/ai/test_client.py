"""AIClient tests — uses a stub LiteLLM response so no network is needed."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from xtv_support.infrastructure.ai.client import AIClient, AIConfig, AIResult


# ----------------------------------------------------------------------
# AIConfig
# ----------------------------------------------------------------------
def test_config_defaults_are_safe() -> None:
    cfg = AIConfig()
    assert cfg.enabled is False
    assert cfg.default_model.startswith("anthropic/")
    assert cfg.max_tokens >= 256
    assert 0.0 <= cfg.temperature <= 2.0


def test_config_from_env_parses_flags() -> None:
    env = {
        "AI_ENABLED": "true",
        "AI_MODEL_DEFAULT": "openai/gpt-4o-mini",
        "AI_MAX_TOKENS": "2048",
        "AI_TEMPERATURE": "0.9",
        "AI_REQUEST_TIMEOUT_S": "45",
        "AI_PII_REDACTION": "false",
    }
    cfg = AIConfig.from_env(env)
    assert cfg.enabled is True
    assert cfg.default_model == "openai/gpt-4o-mini"
    assert cfg.max_tokens == 2048
    assert cfg.temperature == 0.9
    assert cfg.request_timeout_s == 45.0
    assert cfg.redact_pii is False


def test_config_from_env_handles_missing_keys() -> None:
    cfg = AIConfig.from_env({})
    default = AIConfig()
    assert cfg.enabled is False
    assert cfg.default_model == default.default_model


# ----------------------------------------------------------------------
# AIClient — disabled short-circuit
# ----------------------------------------------------------------------
async def test_complete_returns_disabled_result_when_flag_off() -> None:
    client = AIClient(AIConfig(enabled=False))
    result = await client.complete(
        feature="drafts",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result.ok is False
    assert result.error == "ai_disabled"


# ----------------------------------------------------------------------
# AIClient — happy path with stubbed LiteLLM
# ----------------------------------------------------------------------
async def test_complete_parses_provider_response_and_records_usage() -> None:
    usage_inserts: list[dict] = []

    class _AIUsageColl:
        async def insert_one(self, doc):
            usage_inserts.append(doc)

    db = SimpleNamespace(ai_usage=_AIUsageColl())
    client = AIClient(AIConfig(enabled=True), db=db)

    async def fake_litellm(**kwargs):
        return {
            "choices": [{"message": {"content": "  Hello from AI.  "}}],
            "usage": {"prompt_tokens": 42, "completion_tokens": 17},
            "_cost_usd": 0.00042,
        }

    client._call_litellm = fake_litellm  # type: ignore[assignment]

    result = await client.complete(
        feature="drafts",
        messages=[{"role": "user", "content": "hi"}],
        user_id=99,
        ticket_id="t1",
    )
    assert result.ok is True
    assert result.text == "Hello from AI."
    assert result.feature == "drafts"
    assert result.prompt_tokens == 42
    assert result.completion_tokens == 17
    assert result.cost_usd == 0.00042
    assert len(usage_inserts) == 1
    row = usage_inserts[0]
    assert row["feature"] == "drafts"
    assert row["user_id"] == 99
    assert row["ticket_id"] == "t1"


async def test_complete_survives_provider_errors() -> None:
    client = AIClient(AIConfig(enabled=True))

    async def _boom(**_kw):
        raise TimeoutError("provider unreachable")

    client._call_litellm = _boom  # type: ignore[assignment]
    result = await client.complete(
        feature="summary",
        messages=[{"role": "user", "content": "x"}],
    )
    assert result.ok is False
    assert "unreachable" in (result.error or "")


async def test_complete_handles_malformed_response() -> None:
    client = AIClient(AIConfig(enabled=True))

    async def _bad(**_kw):
        return {"not": "what you expected"}

    client._call_litellm = _bad  # type: ignore[assignment]
    result = await client.complete(
        feature="drafts",
        messages=[{"role": "user", "content": "x"}],
    )
    assert result.ok is False
    assert result.error == "bad_response_shape"


# ----------------------------------------------------------------------
# Usage persistence failure is non-fatal
# ----------------------------------------------------------------------
async def test_usage_write_failure_does_not_break_the_call() -> None:
    class _Boom:
        async def insert_one(self, _doc):
            raise RuntimeError("mongo hiccup")

    db = SimpleNamespace(ai_usage=_Boom())
    client = AIClient(AIConfig(enabled=True), db=db)

    async def fake(**_kw):
        return {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

    client._call_litellm = fake  # type: ignore[assignment]
    result = await client.complete(
        feature="sentiment",
        messages=[{"role": "user", "content": "x"}],
    )
    assert result.ok is True
    assert result.text == "ok"
