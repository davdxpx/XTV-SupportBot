"""Plugin lifecycle events (emitted by the plugin loader in Phase 3c)."""
from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class PluginLoaded(DomainEvent):
    name: str
    version: str
    source: str  # builtin | entry_point | path


@dataclass(frozen=True, slots=True, kw_only=True)
class PluginUnloaded(DomainEvent):
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PluginFailed(DomainEvent):
    name: str
    stage: str  # import | startup | handlers | migrations
    error: str
