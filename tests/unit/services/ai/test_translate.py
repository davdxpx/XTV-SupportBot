"""Auto-translation tests."""
from __future__ import annotations

from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.services.ai.translate import translate


async def test_empty_input_is_noop() -> None:
    client = AIClient(AIConfig(enabled=True))
    r = await translate(client, source_text="", target_lang="en")
    assert r.ok
    assert r.translated == ""
    assert r.same_as_source


async def test_translate_happy_path() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [{"message": {"content": "Hello, world!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

    client._call_litellm = fake
    r = await translate(client, source_text="Hallo Welt!", target_lang="English")
    assert r.ok
    assert r.translated == "Hello, world!"
    assert not r.same_as_source


async def test_translate_detects_noop_response() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [{"message": {"content": "Hello, world!"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        }

    client._call_litellm = fake
    r = await translate(
        client, source_text="Hello, world!", target_lang="English"
    )
    assert r.ok
    assert r.same_as_source


async def test_translate_disabled_returns_source() -> None:
    client = AIClient(AIConfig(enabled=False))
    r = await translate(client, source_text="hola", target_lang="English")
    assert not r.ok
    assert r.translated == "hola"
    assert r.error == "ai_disabled"
