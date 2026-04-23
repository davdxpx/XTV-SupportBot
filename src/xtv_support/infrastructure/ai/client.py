"""LiteLLM adapter.

Thin async wrapper around :mod:`litellm` that gives the rest of the
code base a single typed interface regardless of the underlying
provider (Anthropic / OpenAI / Gemini / Ollama / …). LiteLLM itself
handles provider selection via the ``model`` argument.

Design choices
--------------
* **Provider-agnostic** — callers pick a model string; LiteLLM resolves
  which API key to use. ``model="anthropic/claude-sonnet-4-5"`` hits
  Anthropic, ``model="gpt-4o-mini"`` hits OpenAI, ``model="ollama/llama3"``
  hits a local Ollama daemon. Set the relevant key in the environment.

* **Opt-in only** — the whole module is imported lazily from feature
  plugins. ``AIClient.enabled`` reflects the ``AI_ENABLED`` setting and
  feature flags gate individual calls.

* **Cost-aware** — every successful call logs to the ``ai_usage``
  collection (feature, model, tokens, usd_cost, user/ticket ids).
  Phase 9 builds the dashboards; we write the records now.

* **Failure isolation** — every entry point returns an ``AIResult``
  with ``ok`` + ``error``. Plugins never raise on AI hiccups; they
  just skip the feature for that update.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from xtv_support.core.logger import get_logger
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

_log = get_logger("ai.client")


# ----------------------------------------------------------------------
# Data types
# ----------------------------------------------------------------------
@dataclass(slots=True)
class AIConfig:
    """Runtime configuration for the AI layer."""

    enabled: bool = False
    default_model: str = "anthropic/claude-sonnet-4-5"
    fast_model: str = "anthropic/claude-haiku-4-5"
    vision_model: str = "anthropic/claude-sonnet-4-5"
    transcribe_model: str = "openai/whisper-1"
    max_tokens: int = 1024
    temperature: float = 0.4
    request_timeout_s: float = 30.0
    redact_pii: bool = True

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "AIConfig":
        import os

        src = env if env is not None else os.environ
        bool_truthy = {"1", "true", "yes", "on"}

        def _get(key: str, default: str) -> str:
            return src.get(key, default).strip()

        # slots=True removes class-level field defaults, so we build a
        # pristine instance first and pull defaults off it.
        defaults = cls()
        return cls(
            enabled=_get("AI_ENABLED", "false").lower() in bool_truthy,
            default_model=_get("AI_MODEL_DEFAULT", defaults.default_model),
            fast_model=_get("AI_MODEL_FAST", defaults.fast_model),
            vision_model=_get("AI_MODEL_VISION", defaults.vision_model),
            transcribe_model=_get(
                "AI_MODEL_TRANSCRIBE", defaults.transcribe_model
            ),
            max_tokens=int(_get("AI_MAX_TOKENS", str(defaults.max_tokens))),
            temperature=float(_get("AI_TEMPERATURE", str(defaults.temperature))),
            request_timeout_s=float(
                _get("AI_REQUEST_TIMEOUT_S", str(defaults.request_timeout_s))
            ),
            redact_pii=_get("AI_PII_REDACTION", "true").lower() in bool_truthy,
        )


@dataclass(slots=True)
class AIResult:
    """Outcome of one AI call — never raises, always a value."""

    ok: bool
    text: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    feature: str = ""
    error: str | None = None
    raw: Any = None   # full provider response for plugins that want it


@dataclass(slots=True)
class UsageRecord:
    """Row persisted to ``ai_usage`` for each successful call."""

    feature: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    user_id: int | None
    ticket_id: str | None
    ts: Any = field(default_factory=utcnow)


# ----------------------------------------------------------------------
# Client
# ----------------------------------------------------------------------
class AIClient:
    """Minimal async facade over LiteLLM.

    No ``__slots__`` on purpose — tests monkeypatch ``_call_litellm`` as
    an instance attribute so they don't need the real litellm package.
    """

    def __init__(
        self,
        config: AIConfig,
        db: "AsyncIOMotorDatabase | None" = None,
    ) -> None:
        self.config = config
        self._db = db

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------
    async def complete(
        self,
        *,
        feature: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        user_id: int | None = None,
        ticket_id: str | None = None,
    ) -> AIResult:
        """Run a chat-completion and return a structured result."""
        if not self.config.enabled:
            return AIResult(ok=False, feature=feature, error="ai_disabled")

        model = model or self.config.default_model
        try:
            response = await self._call_litellm(
                model=model,
                messages=messages,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=(
                    temperature if temperature is not None else self.config.temperature
                ),
                timeout=self.config.request_timeout_s,
            )
        except Exception as exc:  # noqa: BLE001 — never raise into callers
            _log.warning(
                "ai.call_failed",
                feature=feature,
                model=model,
                error=str(exc),
            )
            return AIResult(ok=False, feature=feature, model=model, error=str(exc))

        try:
            text = response["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            _log.warning("ai.bad_response_shape", feature=feature, error=str(exc))
            return AIResult(
                ok=False, feature=feature, model=model, error="bad_response_shape"
            )

        usage = response.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cost = float(response.get("_cost_usd") or response.get("cost_usd") or 0.0)

        result = AIResult(
            ok=True,
            text=text.strip(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            feature=feature,
            raw=response,
        )
        await self._record_usage(
            UsageRecord(
                feature=feature,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                user_id=user_id,
                ticket_id=ticket_id,
            )
        )
        return result

    # ------------------------------------------------------------------
    # Overridable seam — patched in tests to skip the real provider.
    # ------------------------------------------------------------------
    async def _call_litellm(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> dict[str, Any]:
        """Actual LiteLLM invocation. Imported lazily so the module stays
        importable without the ``ai`` extra installed.
        """
        try:
            import litellm  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "litellm is not installed — install the `ai` extra: "
                "pip install -e '.[ai]'"
            ) from exc

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        return response if isinstance(response, dict) else response.model_dump()

    # ------------------------------------------------------------------
    # Usage persistence — best effort; never blocks the caller.
    # ------------------------------------------------------------------
    async def _record_usage(self, record: UsageRecord) -> None:
        if self._db is None:
            return
        try:
            await self._db.ai_usage.insert_one(
                {
                    "feature": record.feature,
                    "model": record.model,
                    "prompt_tokens": record.prompt_tokens,
                    "completion_tokens": record.completion_tokens,
                    "cost_usd": record.cost_usd,
                    "user_id": record.user_id,
                    "ticket_id": record.ticket_id,
                    "ts": record.ts,
                }
            )
        except Exception as exc:  # noqa: BLE001
            _log.debug("ai.usage_write_failed", error=str(exc))
