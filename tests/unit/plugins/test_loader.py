"""PluginLoader tests — discovery, flag gating, lifecycle isolation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xtv_support.core.container import Container
from xtv_support.core.events import EventBus
from xtv_support.domain.events import PluginFailed, PluginLoaded, TicketCreated
from xtv_support.plugins.base import CommandSpec, EventSubscription, Plugin
from xtv_support.plugins.loader import PluginLoader


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------
class _Flags:
    """Minimal FeatureFlags stand-in."""

    def __init__(self, enabled: dict[str, bool] | None = None) -> None:
        self._enabled = enabled or {}

    def is_enabled(self, name: str) -> bool:
        return bool(self._enabled.get(name.upper()))


class _OkPlugin(Plugin):
    name = "ok"
    version = "1.0"

    def __init__(self) -> None:
        self.started_with: Container | None = None
        self.shutdown_called = False
        self.hits: list[TicketCreated] = []

    async def on_startup(self, container: Container) -> None:
        self.started_with = container

    async def on_shutdown(self) -> None:
        self.shutdown_called = True

    def register_commands(self) -> list[CommandSpec]:
        return [CommandSpec(name="ok", scope="admin", summary="ok")]

    def subscribe_events(self) -> list[EventSubscription]:
        async def on_ticket(e: TicketCreated) -> None:
            self.hits.append(e)

        return [EventSubscription(event_type=TicketCreated, handler=on_ticket)]


class _FlagGated(Plugin):
    name = "gated"
    version = "1.0"
    feature_flag = "MY_FLAG"

    started = False

    async def on_startup(self, container: Container) -> None:
        self.started = True  # type: ignore[misc]


class _BoomPlugin(Plugin):
    name = "boom"
    version = "1.0"

    async def on_startup(self, container: Container) -> None:
        raise RuntimeError("bang during startup")


class _BadNamePlugin(Plugin):
    name = "Has Spaces!"
    version = "1.0"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@dataclass
class _Rig:
    loader: PluginLoader
    bus: EventBus
    container: Container
    flags: _Flags
    events_seen: list[Any]


def _build_rig(flags: _Flags | None = None) -> _Rig:
    bus = EventBus()
    container = Container()
    flg = flags or _Flags()
    loader = PluginLoader(container=container, bus=bus, flags=flg)
    seen: list[Any] = []

    def record(e: Any) -> None:
        seen.append(e)

    # Subscribe to plugin lifecycle events for assertions.
    bus.subscribe(PluginLoaded, record)
    bus.subscribe(PluginFailed, record)

    return _Rig(loader=loader, bus=bus, container=container, flags=flg, events_seen=seen)


# --------------------------------------------------------------------------
# Tests — activate via the private _activate so we don't rely on the
# filesystem-side discovery walk. Discovery itself is covered by
# test_discovers_builtin_healthcheck below.
# --------------------------------------------------------------------------
async def test_activate_ok_plugin_runs_lifecycle_and_wires_events() -> None:
    rig = _build_rig()
    entry = await rig.loader._activate(_OkPlugin, "builtin")
    assert entry is not None
    assert entry.status == "loaded"
    assert entry.commands and entry.commands[0].name == "ok"
    assert rig.bus.handler_count(TicketCreated) == 1

    # Publishing a ticket must reach the plugin's handler.
    await rig.bus.publish(TicketCreated(ticket_id="t1", user_id=1))
    assert len(entry.plugin.hits) == 1  # type: ignore[attr-defined]

    # PluginLoaded was emitted.
    loaded_events = [e for e in rig.events_seen if isinstance(e, PluginLoaded)]
    assert len(loaded_events) == 1
    assert loaded_events[0].name == "ok"


async def test_startup_failure_is_isolated_and_emits_pluginfailed() -> None:
    rig = _build_rig()
    entry = await rig.loader._activate(_BoomPlugin, "builtin")
    assert entry is not None
    assert entry.status == "failed"
    assert entry.error and "bang" in entry.error
    failed = [e for e in rig.events_seen if isinstance(e, PluginFailed)]
    assert failed and failed[0].name == "boom" and failed[0].stage == "startup"


async def test_feature_flag_disables_plugin() -> None:
    rig = _build_rig(flags=_Flags({"MY_FLAG": False}))
    entry = await rig.loader._activate(_FlagGated, "builtin")
    assert entry is not None
    assert entry.status == "disabled"
    # No PluginLoaded / PluginFailed emitted for disabled plugins.
    assert not any(isinstance(e, (PluginLoaded, PluginFailed)) for e in rig.events_seen)


async def test_feature_flag_true_activates_plugin() -> None:
    rig = _build_rig(flags=_Flags({"MY_FLAG": True}))
    entry = await rig.loader._activate(_FlagGated, "builtin")
    assert entry is not None
    assert entry.status == "loaded"


async def test_duplicate_plugin_name_is_skipped() -> None:
    rig = _build_rig()
    a = await rig.loader._activate(_OkPlugin, "builtin")
    b = await rig.loader._activate(_OkPlugin, "builtin")
    assert a is not None and a.status == "loaded"
    assert b is None
    assert len(rig.loader.registry) == 1


async def test_invalid_name_is_rejected() -> None:
    rig = _build_rig()
    entry = await rig.loader._activate(_BadNamePlugin, "builtin")
    assert entry is None
    assert len(rig.loader.registry) == 0


async def test_unload_all_calls_shutdown_and_detaches_subscribers() -> None:
    rig = _build_rig()
    entry = await rig.loader._activate(_OkPlugin, "builtin")
    assert entry and entry.status == "loaded"
    assert rig.bus.handler_count(TicketCreated) == 1
    await rig.loader.unload_all()
    # Subscription removed
    assert rig.bus.handler_count(TicketCreated) == 0
    # Plugin learned it's shutting down
    assert entry.plugin.shutdown_called is True  # type: ignore[attr-defined]


async def test_discovers_builtin_healthcheck() -> None:
    rig = _build_rig()
    await rig.loader.load_all()
    names = {e.plugin.name for e in rig.loader.registry}
    assert "healthcheck" in names
    hc = rig.loader.registry.get("healthcheck")
    assert hc is not None
    assert hc.status == "loaded"
    assert hc.source == "builtin"
