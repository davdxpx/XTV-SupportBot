"""Feature flags.

A thin :class:`pydantic_settings.BaseSettings` over env variables prefixed
with ``FEATURE_``. Flags are read once at boot and cached; for true
runtime flipping a later phase will back these with a MongoDB collection
and a pub/sub invalidation event.

Example
-------
``FEATURE_AI_DRAFTS=true`` in ``.env`` flips on the AI reply-draft plugin.

``python
from xtv_support.config.flags import flags

if flags.AI_DRAFTS:
    ...
``
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseSettings):
    """All opt-in features, default off unless flagged otherwise."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FEATURE_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- AI (Phase 7) ---------------------------------------------------
    AI_DRAFTS: bool = False
    AI_SUMMARY: bool = False
    AI_SENTIMENT: bool = False
    AI_ROUTING: bool = False
    AI_TRANSLATE: bool = False
    AI_TRANSCRIBE: bool = False
    AI_KB_DRAFTER: bool = False

    # --- Business logic (Phases 6, 8, 9) --------------------------------
    BUSINESS_HOURS: bool = False
    CSAT: bool = False
    ANALYTICS_DIGEST: bool = False
    KB_GATE: bool = False

    # --- Security / anti-abuse (Phase 12) -------------------------------
    LINK_SCANNER: bool = True
    START_CAPTCHA: bool = False

    # --- Integrations (Phase 10) ----------------------------------------
    WEBHOOKS_OUT: bool = False
    DISCORD_BRIDGE: bool = False
    SLACK_BRIDGE: bool = False
    EMAIL_INGRESS: bool = False

    def is_enabled(self, name: str) -> bool:
        """Lookup helper for dynamic names: ``flags.is_enabled("ai_drafts")``."""
        attr = name.upper()
        value = getattr(self, attr, None)
        return bool(value) if value is not None else False


@lru_cache(maxsize=1)
def get_flags() -> FeatureFlags:
    """Cached factory — tests can call :func:`FeatureFlags` directly to bypass."""
    return FeatureFlags()  # type: ignore[call-arg]


flags: FeatureFlags = get_flags()
