"""Runtime settings schema + resolver.

Overlays admin-editable overrides (from :mod:`xtv_support.infrastructure.db.
app_settings`) on top of the env defaults in :mod:`xtv_support.config.settings`,
so operators can tune operational knobs live without a redeploy. The allowlist
below is the single source of truth for what is editable — secrets and infra
settings are intentionally excluded and can never be set through this path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from xtv_support.config import settings as _settings_mod


@dataclass(frozen=True)
class SettingSpec:
    key: str
    type: str  # "int" | "str" | "choice"
    section: str
    label: str
    help: str = ""
    min: int | None = None
    max: int | None = None
    choices: tuple[str, ...] | None = None


SPECS: tuple[SettingSpec, ...] = (
    SettingSpec("SLA_WARN_MINUTES", "int", "SLA", "Warn after (min)", min=1, max=100000),
    SettingSpec("SLA_BREACH_MINUTES", "int", "SLA", "Breach after (min)", min=1, max=100000),
    SettingSpec(
        "AUTO_CLOSE_DAYS", "int", "Tickets", "Auto-close idle after (days)", min=1, max=365
    ),
    SettingSpec(
        "AUTO_CLOSE_SWEEP_MINUTES",
        "int",
        "Tickets",
        "Auto-close sweep every (min)",
        min=1,
        max=1440,
    ),
    SettingSpec(
        "TOPIC_DELETE_AFTER_CLOSE_MINUTES",
        "int",
        "Tickets",
        "Delete topic after close (min)",
        help="0 disables — topics are only closed, never deleted.",
        min=0,
        max=525600,
    ),
    SettingSpec(
        "TOPIC_CLEANUP_SWEEP_MINUTES",
        "int",
        "Tickets",
        "Topic cleanup sweep every (min)",
        min=1,
        max=1440,
    ),
    SettingSpec("COOLDOWN_RATE", "int", "Anti-spam", "Messages per window", min=1, max=1000),
    SettingSpec("COOLDOWN_WINDOW", "int", "Anti-spam", "Window (sec)", min=1, max=3600),
    SettingSpec(
        "COOLDOWN_MUTE_SECONDS", "int", "Anti-spam", "Mute duration (sec)", min=1, max=86400
    ),
    SettingSpec("BROADCAST_CONCURRENCY", "int", "Broadcast", "Concurrent sends", min=1, max=100),
    SettingSpec(
        "BROADCAST_FLOOD_BUFFER_MS", "int", "Broadcast", "Flood buffer (ms)", min=0, max=10000
    ),
    SettingSpec("BRAND_NAME", "str", "Branding", "Brand name", max=64),
    SettingSpec("BRAND_TAGLINE", "str", "Branding", "Brand tagline", max=160),
    SettingSpec("UI_MODE", "choice", "UI", "Default UI mode", choices=("chat", "webapp", "hybrid")),
    SettingSpec("DEFAULT_LANG", "str", "UI", "Default language code", max=10),
)

SPEC_BY_KEY: dict[str, SettingSpec] = {s.key: s for s in SPECS}


def default_for(key: str) -> Any:
    # Read the live module attribute (not a captured reference) so tests that
    # swap ``settings`` — and any future settings reload — are reflected.
    return getattr(_settings_mod.settings, key)


def coerce(spec: SettingSpec, raw: Any) -> Any:
    """Validate + convert a raw override value. Raises ``ValueError`` if bad."""
    if spec.type == "int":
        value = int(raw)
        if spec.min is not None and value < spec.min:
            raise ValueError(f"{spec.key} < {spec.min}")
        if spec.max is not None and value > spec.max:
            raise ValueError(f"{spec.key} > {spec.max}")
        return value
    if spec.type == "choice":
        value = str(raw)
        if spec.choices and value not in spec.choices:
            raise ValueError(f"{spec.key} not in {spec.choices}")
        return value
    value = str(raw)
    if spec.max is not None and len(value) > spec.max:
        raise ValueError(f"{spec.key} too long")
    return value


# --- resolver + tiny TTL cache (single-process bot+API) ---
_cache: dict[str, Any] | None = None
_cache_at: float = 0.0
_TTL = 10.0


def invalidate() -> None:
    global _cache
    _cache = None


async def _overrides(db: Any) -> dict[str, Any]:
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and now - _cache_at < _TTL:
        return _cache
    from xtv_support.infrastructure.db import app_settings as store

    _cache = await store.get_overrides(db)
    _cache_at = now
    return _cache


def _value(key: str, overrides: dict[str, Any]) -> Any:
    spec = SPEC_BY_KEY[key]
    if key in overrides:
        try:
            return coerce(spec, overrides[key])
        except (ValueError, TypeError):
            pass  # bad stored value → fall back to the env default
    return default_for(key)


class RuntimeSettings:
    """Attribute/`.get` access to the resolved (override-or-default) values."""

    def __init__(self, overrides: dict[str, Any]) -> None:
        self._overrides = overrides

    def get(self, key: str) -> Any:
        return _value(key, self._overrides)

    def __getattr__(self, key: str) -> Any:
        if key in SPEC_BY_KEY:
            return _value(key, self._overrides)
        raise AttributeError(key)


async def get_runtime(db: Any) -> RuntimeSettings:
    return RuntimeSettings(await _overrides(db))


def describe(overrides: dict[str, Any]) -> list[dict[str, Any]]:
    """Schema + current value for each editable setting (for the settings API)."""
    out: list[dict[str, Any]] = []
    for spec in SPECS:
        out.append(
            {
                "key": spec.key,
                "type": spec.type,
                "section": spec.section,
                "label": spec.label,
                "help": spec.help,
                "min": spec.min,
                "max": spec.max,
                "choices": list(spec.choices) if spec.choices else None,
                "value": _value(spec.key, overrides),
                "default": default_for(spec.key),
                "overridden": spec.key in overrides,
            }
        )
    return out
