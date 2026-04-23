"""Plugin contract.

A plugin is a regular Python package that exposes a single :class:`Plugin`
subclass (or a zero-arg callable that returns one) through the
``xtv_support.plugins`` entry-point group in its ``pyproject.toml``::

    [project.entry-points."xtv_support.plugins"]
    my_plugin = "my_plugin:Plugin"

First-party plugins live under :mod:`xtv_support.plugins.builtin` and are
auto-discovered by the loader.

The contract is intentionally minimal so existing code can adopt it
without a large refactor:

* **Metadata** — ``name``, ``version`` and an optional ``feature_flag``
  (when set and falsy, the plugin is skipped at load time).
* **Lifecycle hooks** — ``on_startup`` / ``on_shutdown``.
* **Integration hooks** — ``register_handlers``, ``register_commands``,
  ``subscribe_events``, ``migrations``.

Any hook returning ``None`` (the default) means the plugin opts out of
that extension point, so most plugins only override one or two methods.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover — type-only
    from xtv_support.core.container import Container
    from xtv_support.core.events import EventBus
    from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Declarative description of a slash command contributed by a plugin."""

    name: str                 # "macro" (user types /macro)
    scope: str                # "user" | "admin" | "topic" | "system" | "agent"
    summary: str              # one-line help text
    hidden: bool = False      # do not advertise in /help
    feature_flag: str | None = None  # gate the command on a FEATURE_* flag


@dataclass(frozen=True, slots=True)
class MigrationSpec:
    """Zero-arg async callable that brings the DB up to a target schema version."""

    name: str
    version: int
    run: Callable[..., Awaitable[None]]


@dataclass(frozen=True, slots=True)
class EventSubscription:
    """Pair of event class + handler the loader wires into the bus."""

    event_type: type["DomainEvent"]
    handler: Callable[[Any], Awaitable[None] | None]


class Plugin:
    """Concrete base class — subclass this for built-in plugins.

    Every hook is a no-op by default so subclasses override just the
    pieces they need.
    """

    #: Stable, filesystem-safe identifier (``[a-z0-9_-]{1,32}``).
    name: str = ""
    #: SemVer string. Displayed on ``/admin » Plugins``.
    version: str = "0.0.1"
    #: When set, :class:`PluginLoader` skips the plugin unless the named
    #: flag on :class:`xtv_support.config.flags.FeatureFlags` is truthy.
    feature_flag: str | None = None
    #: Optional human-readable one-liner.
    description: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def on_startup(self, container: "Container") -> None:  # noqa: D401
        """Run once, after the container and event bus are built."""

    async def on_shutdown(self) -> None:
        """Run once, during graceful shutdown."""

    # ------------------------------------------------------------------
    # Integration hooks — the loader queries these synchronously right
    # after on_startup, so plugins return cheap, immutable specs.
    # ------------------------------------------------------------------
    def register_commands(self) -> list[CommandSpec]:
        return []

    def subscribe_events(self) -> list[EventSubscription]:
        return []

    def register_handlers(self, router: Any) -> None:
        """Hook for handler groups. Kept as ``Any`` — Phase 3d provides the type."""

    def migrations(self) -> list[MigrationSpec]:
        return []


@runtime_checkable
class PluginLike(Protocol):
    """Structural type-check for duck-typed plugins (e.g. from factories)."""

    name: str
    version: str

    async def on_startup(self, container: "Container") -> None: ...
    async def on_shutdown(self) -> None: ...
    def register_commands(self) -> list[CommandSpec]: ...
    def subscribe_events(self) -> list[EventSubscription]: ...
    def register_handlers(self, router: Any) -> None: ...
    def migrations(self) -> list[MigrationSpec]: ...


@dataclass(slots=True)
class LoadedPlugin:
    """Registry entry tracking a plugin's runtime state."""

    plugin: Plugin
    source: str                    # "builtin" | "entry_point" | "path"
    status: str = "pending"        # pending | loaded | failed | disabled
    error: str | None = None
    commands: list[CommandSpec] = field(default_factory=list)
    subscriptions: list[EventSubscription] = field(default_factory=list)
