"""Voice/image transcription tests.

Voice tests run without the real litellm package by monkey-patching
the dynamic import to a stub module.
"""
from __future__ import annotations

import sys
import types

import pytest

from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.services.ai.transcribe import (
    _extract_text,
    transcribe_image,
    transcribe_voice,
)


# ----------------------------------------------------------------------
# _extract_text normaliser
# ----------------------------------------------------------------------
def test_extract_text_from_dict() -> None:
    assert _extract_text({"text": "hello"}) == "hello"


def test_extract_text_from_attr_object() -> None:
    class Obj:
        text = "world"

    assert _extract_text(Obj()) == "world"


def test_extract_text_none() -> None:
    assert _extract_text(None) == ""


def test_extract_text_unknown_shape() -> None:
    assert _extract_text(object()) == ""


# ----------------------------------------------------------------------
# transcribe_voice
# ----------------------------------------------------------------------
async def test_transcribe_voice_disabled() -> None:
    client = AIClient(AIConfig(enabled=False))
    r = await transcribe_voice(
        client, audio_bytes=b"...", filename="a.ogg"
    )
    assert not r.ok
    assert r.kind == "voice"
    assert r.error == "ai_disabled"


async def test_transcribe_voice_happy_with_stub_litellm(monkeypatch) -> None:
    async def fake_atranscription(**kw):
        return {"text": "hello there"}

    fake_module = types.SimpleNamespace(atranscription=fake_atranscription)
    monkeypatch.setitem(sys.modules, "litellm", fake_module)

    client = AIClient(AIConfig(enabled=True))
    r = await transcribe_voice(
        client, audio_bytes=b"blob", filename="a.ogg", ticket_id="t1"
    )
    assert r.ok
    assert r.text == "hello there"
    assert r.kind == "voice"


async def test_transcribe_voice_provider_error(monkeypatch) -> None:
    async def boom(**kw):
        raise RuntimeError("provider down")

    fake_module = types.SimpleNamespace(atranscription=boom)
    monkeypatch.setitem(sys.modules, "litellm", fake_module)

    client = AIClient(AIConfig(enabled=True))
    r = await transcribe_voice(client, audio_bytes=b"x", filename="a.ogg")
    assert not r.ok
    assert "provider down" in (r.error or "")


# ----------------------------------------------------------------------
# transcribe_image
# ----------------------------------------------------------------------
async def test_transcribe_image_disabled() -> None:
    client = AIClient(AIConfig(enabled=False))
    r = await transcribe_image(client, image_url="https://x/y.png")
    assert not r.ok
    assert r.kind == "image"
    assert r.error == "ai_disabled"


async def test_transcribe_image_happy_path() -> None:
    client = AIClient(AIConfig(enabled=True, redact_pii=False))

    async def fake(**kw):
        return {
            "choices": [{"message": {"content": "A screenshot of an error dialog."}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 8},
        }

    client._call_litellm = fake
    r = await transcribe_image(client, image_url="https://x/y.png")
    assert r.ok
    assert r.kind == "image"
    assert "screenshot" in r.text.lower()
