"""Voice / image transcription service.

Thin wrapper around the :class:`AIClient` transcription API. For
voice we rely on LiteLLM's ``atranscription`` (whisper-compatible);
for images we route the bytes through a vision-capable chat completion
with a ``[image]`` user-content block.

Callers provide already-downloaded bytes + the original filename. The
pyrofork handler in the plugin is responsible for actually pulling
the file from Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.ai.client import AIClient

if TYPE_CHECKING:  # pragma: no cover
    pass

log = get_logger("ai.transcribe")


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    text: str
    kind: str  # "voice" | "image"
    ok: bool
    model: str = ""
    error: str | None = None


async def transcribe_voice(
    client: AIClient,
    *,
    audio_bytes: bytes,
    filename: str,
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> TranscriptionResult:
    """Run speech-to-text on a voice clip."""
    if not client.config.enabled:
        return TranscriptionResult(text="", kind="voice", ok=False, error="ai_disabled")
    try:
        import litellm  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:
        return TranscriptionResult(text="", kind="voice", ok=False, error=f"litellm_missing: {exc}")

    model = client.config.transcribe_model
    try:
        response = await litellm.atranscription(
            model=model,
            file=(filename, audio_bytes),
            timeout=client.config.request_timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "ai.transcribe_voice.failed",
            model=model,
            ticket_id=ticket_id,
            error=str(exc),
        )
        return TranscriptionResult(text="", kind="voice", ok=False, model=model, error=str(exc))

    text = _extract_text(response)
    log.info(
        "ai.transcribe_voice.ok",
        model=model,
        ticket_id=ticket_id,
        chars=len(text),
    )
    return TranscriptionResult(text=text, kind="voice", ok=True, model=model)


async def transcribe_image(
    client: AIClient,
    *,
    image_url: str,
    user_id: int | None = None,
    ticket_id: str | None = None,
) -> TranscriptionResult:
    """Run vision-chat to extract text / describe an image.

    Accepts an ``image_url`` (Telegram files need to be uploaded to a
    temporary URL the provider can fetch, or passed inline as base64
    data URL — the caller decides).
    """
    if not client.config.enabled:
        return TranscriptionResult(text="", kind="image", ok=False, error="ai_disabled")

    messages = [
        {
            "role": "system",
            "content": (
                "Describe the image concisely. If it contains text, "
                "transcribe the text verbatim. Respond in the same "
                "language the text uses."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
                {"type": "text", "text": "What does this image show?"},
            ],
        },
    ]
    result = await client.complete(
        feature="transcribe_image",
        messages=messages,
        model=client.config.vision_model,
        user_id=user_id,
        ticket_id=ticket_id,
    )
    if not result.ok:
        return TranscriptionResult(
            text="",
            kind="image",
            ok=False,
            model=client.config.vision_model,
            error=result.error or "ai_call_failed",
        )
    log.info(
        "ai.transcribe_image.ok",
        model=client.config.vision_model,
        ticket_id=ticket_id,
        chars=len(result.text),
    )
    return TranscriptionResult(
        text=result.text,
        kind="image",
        ok=True,
        model=client.config.vision_model,
    )


def _extract_text(response) -> str:
    """LiteLLM's atranscription returns objects with a ``text`` attr
    or dicts with a ``text`` key, depending on the provider. Try both.
    """
    if response is None:
        return ""
    if isinstance(response, dict):
        return str(response.get("text") or "")
    text = getattr(response, "text", None)
    if text is not None:
        return str(text)
    try:
        return str(response.model_dump().get("text") or "")
    except Exception:  # noqa: BLE001
        return ""
