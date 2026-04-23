"""Plugin discovery + lifecycle.

Two discovery sources:

1. **Built-ins** under :mod:`xtv_support.plugins.builtin` — every
   immediate sub-package that exposes a module-level ``Plugin`` class
   (subclass of :class:`xtv_support.plugins.base.Plugin`).
2. **Third-party** installed packages that declare the
   ``xtv_support.plugins`` entry-point group in their ``pyproject.toml``.

For each plugin the loader:

* Creates an instance (plugin factory may be a class or a zero-arg callable).
* Checks the optional ``feature_flag`` against
  :class:`xtv_support.config.flags.FeatureFlags`. If falsy, the plugin is
  marked ``disabled`` and skipped.
* Runs ``on_startup(container)``.
* Wires ``subscribe_events()`` into the bus and collects ``register_commands()``.
* Publishes :class:`xtv_support.domain.events.plugins.PluginLoaded` on success,
  :class:`PluginFailed` otherwise.

Failures are isolated — one misbehaving plugin never prevents the rest
from loading.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from collections.abc import Callable
from importlib.metadata import EntryPoint, entry_points
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import PluginFailed, PluginLoaded, PluginUnloaded
from xtv_support.plugins.base import EventSubscription, LoadedPlugin, Plugin
from xtv_support.plugins.registry import PluginRegistry

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.config.flags import FeatureFlags
    from xtv_support.core.container import Container
    from xtv_support.core.events import EventBus

_log = get_logger("plugins.loader")

_BUILTIN_PACKAGE = "xtv_support.plugins.builtin"
_ENTRY_POINT_GROUP = "xtv_support.plugins"

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class PluginLoadError(RuntimeError):
    """Raised when an invariant of the plugin contract is violated."""


class PluginLoader:
    """Discovers, instantiates and activates plugins."""

    __slots__ = ("_container", "_bus", "_flags", "_registry")

    def __init__(
        self,
        *,
        container: "Container",
        bus: "EventBus",
        flags: "FeatureFlags | None" = None,
        registry: PluginRegistry | None = None,
    ) -> None:
        self._container = container
        self._bus = bus
        self._flags = flags
        self._registry = registry or PluginRegistry()

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def load_all(self) -> PluginRegistry:
        """Discover and activate every enabled plugin."""
        for factory, source in self._discover():
            await self._activate(factory, source)
        _log.info(
            "plugins.loaded",
            total=len(self._registry),
            loaded=len(self._registry.loaded()),
            failed=len(self._registry.failed()),
            disabled=len(self._registry.disabled()),
        )
        return self._registry

    async def unload_all(self) -> None:
        for entry in list(self._registry):
            if entry.status != "loaded":
                continue
            try:
                await entry.plugin.on_shutdown()
            except Exception as exc:  # noqa: BLE001
                _log.exception(
                    "plugin.shutdown_failed",
                    plugin=entry.plugin.name,
                    error=str(exc),
                )
            # Detach event subscriptions so the bus no longer fires into us.
            for sub in entry.subscriptions:
                self._bus.unsubscribe(sub.event_type, sub.handler)
            await self._bus.publish(PluginUnloaded(name=entry.plugin.name))

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def _discover(self) -> list[tuple[Callable[[], Plugin], str]]:
        found: list[tuple[Callable[[], Plugin], str]] = []
        found.extend(self._discover_builtins())
        found.extend(self._discover_entry_points())
        return found

    def _discover_builtins(self) -> list[tuple[Callable[[], Plugin], str]]:
        try:
            pkg = importlib.import_module(_BUILTIN_PACKAGE)
        except ModuleNotFoundError:
            return []
        result: list[tuple[Callable[[], Plugin], str]] = []
        for info in pkgutil.iter_modules(pkg.__path__, prefix=f"{_BUILTIN_PACKAGE}."):
            try:
                module = importlib.import_module(info.name)
            except Exception as exc:  # noqa: BLE001
                _log.exception(
                    "plugin.builtin_import_failed", module=info.name, error=str(exc)
                )
                continue
            factory = _factory_from_module(module)
            if factory is not None:
                result.append((factory, "builtin"))
        return result

    def _discover_entry_points(self) -> list[tuple[Callable[[], Plugin], str]]:
        result: list[tuple[Callable[[], Plugin], str]] = []
        try:
            eps = entry_points(group=_ENTRY_POINT_GROUP)
        except TypeError:  # pragma: no cover — python<3.10 API, not applicable
            eps = entry_points().get(_ENTRY_POINT_GROUP, [])  # type: ignore[union-attr]
        for ep in eps:
            try:
                factory = _factory_from_entry_point(ep)
            except Exception as exc:  # noqa: BLE001
                _log.exception(
                    "plugin.entry_point_failed", entry=str(ep), error=str(exc)
                )
                continue
            result.append((factory, "entry_point"))
        return result

    # ------------------------------------------------------------------
    # Activation of one plugin
    # ------------------------------------------------------------------
    async def _activate(
        self, factory: Callable[[], Plugin], source: str
    ) -> LoadedPlugin | None:
        # Instantiate first so we can register even failures with a name.
        try:
            plugin = factory()
        except Exception as exc:  # noqa: BLE001
            _log.exception("plugin.instantiation_failed", error=str(exc))
            await self._bus.publish(
                PluginFailed(name="<unknown>", stage="import", error=str(exc))
            )
            return None

        if not isinstance(plugin, Plugin):
            _log.error("plugin.wrong_type", actual=type(plugin).__name__)
            return None
        if not _NAME_RE.match(plugin.name or ""):
            _log.error("plugin.invalid_name", name=plugin.name)
            return None
        if plugin.name in self._registry:
            _log.warning("plugin.duplicate_skipped", name=plugin.name)
            return None

        entry = LoadedPlugin(plugin=plugin, source=source)
        self._registry.add(entry)

        # Feature-flag gate
        if plugin.feature_flag and self._flags is not None:
            if not self._flags.is_enabled(plugin.feature_flag):
                entry.status = "disabled"
                _log.info(
                    "plugin.disabled_by_flag",
                    plugin=plugin.name,
                    flag=plugin.feature_flag,
                )
                return entry

        # Lifecycle: on_startup
        try:
            await plugin.on_startup(self._container)
        except Exception as exc:  # noqa: BLE001
            entry.status = "failed"
            entry.error = str(exc)
            _log.exception(
                "plugin.startup_failed", plugin=plugin.name, error=str(exc)
            )
            await self._bus.publish(
                PluginFailed(name=plugin.name, stage="startup", error=str(exc))
            )
            return entry

        # Collect commands (pure data)
        try:
            entry.commands = list(plugin.register_commands())
        except Exception as exc:  # noqa: BLE001
            _log.exception(
                "plugin.commands_failed", plugin=plugin.name, error=str(exc)
            )
            entry.commands = []

        # Wire event subscriptions
        try:
            subs = list(plugin.subscribe_events())
            for sub in subs:
                self._bus.subscribe(sub.event_type, sub.handler)
            entry.subscriptions = subs
        except Exception as exc:  # noqa: BLE001
            _log.exception(
                "plugin.subscribe_failed", plugin=plugin.name, error=str(exc)
            )

        entry.status = "loaded"
        await self._bus.publish(
            PluginLoaded(name=plugin.name, version=plugin.version, source=source)
        )
        _log.info(
            "plugin.loaded",
            plugin=plugin.name,
            version=plugin.version,
            source=source,
            commands=len(entry.commands),
            subs=len(entry.subscriptions),
        )
        return entry


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _factory_from_module(module: object) -> Callable[[], Plugin] | None:
    """Look for a ``Plugin`` attribute on ``module`` that is a subclass of :class:`Plugin`."""
    candidate = getattr(module, "Plugin", None)
    if candidate is None:
        return None
    if inspect.isclass(candidate) and issubclass(candidate, Plugin):
        return candidate  # class is itself a zero-arg factory
    if callable(candidate):
        return candidate  # assume factory
    return None


def _factory_from_entry_point(ep: EntryPoint) -> Callable[[], Plugin]:
    """Resolve an entry-point to a zero-arg plugin factory."""
    target = ep.load()
    if inspect.isclass(target) and issubclass(target, Plugin):
        return target
    if callable(target):
        return target
    raise PluginLoadError(
        f"Entry point {ep.name!r} did not resolve to a Plugin subclass or factory; "
        f"got {type(target).__name__}."
    )
