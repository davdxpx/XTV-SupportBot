"""Healthcheck plugin — minimal but real.

Demonstrates every hook the loader calls so future plugins have a
reference to copy. Always loads (no feature flag), owns zero state, and
simply logs when a :class:`PluginLoaded` event fires.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import PluginLoaded
from xtv_support.plugins.base import CommandSpec, EventSubscription, Plugin as _Base

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.healthcheck")


class Plugin(_Base):
    """Always-on self-test plugin."""

    name = "healthcheck"
    version = "0.1.0"
    description = "Verifies the plugin loader is wired up correctly."

    async def on_startup(self, container: "Container") -> None:
        _log.info("healthcheck.startup", loaded=True)

    async def on_shutdown(self) -> None:
        _log.info("healthcheck.shutdown")

    def register_commands(self) -> list[CommandSpec]:
        return [
            CommandSpec(
                name="plugins",
                scope="admin",
                summary="List loaded plugins and their status.",
            )
        ]

    def subscribe_events(self) -> list[EventSubscription]:
        async def _on_loaded(event: PluginLoaded) -> None:
            _log.info(
                "plugin.peer_loaded",
                name=event.name,
                version=event.version,
                source=event.source,
            )

        return [EventSubscription(event_type=PluginLoaded, handler=_on_loaded)]

    def register_handlers(self, router: Any) -> None:
        # Real handlers are wired in later phases — this plugin carries
        # none of its own.
        return None
