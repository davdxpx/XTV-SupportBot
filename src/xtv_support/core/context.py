from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from pyrogram import Client

    from xtv_support.config.flags import FeatureFlags
    from xtv_support.config.settings import Settings
    from xtv_support.core.container import Container
    from xtv_support.core.events import EventBus
    from xtv_support.core.i18n import I18n
    from xtv_support.core.state import StateMachine
    from xtv_support.plugins.loader import PluginLoader
    from xtv_support.plugins.registry import PluginRegistry
    from xtv_support.services.broadcasts.service import BroadcastManager
    from xtv_support.services.cooldown.service import CooldownService
    from xtv_support.services.sla.service import SlaService
    from xtv_support.tasks.scheduler import TaskManager


@dataclass
class HandlerContext:
    """Shared dependencies passed to handlers.

    Pyrofork handlers receive only (client, update). We stash this on the
    Client instance as ``client._ctx`` in ``register_all`` so handlers can
    access it via ``ctx = client._ctx``.

    The original fields (client, settings, db, tasks, cooldown, sla,
    broadcasts) are preserved for backwards compatibility — every existing
    handler continues to work unchanged. The kernel additions (container,
    bus, flags, state, plugin_*) are opt-in; new code can pull services
    from :attr:`container` instead of adding another field here.
    """

    client: "Client"
    settings: "Settings"
    db: "AsyncIOMotorDatabase"
    tasks: "TaskManager"
    cooldown: "CooldownService"
    sla: "SlaService"
    broadcasts: "BroadcastManager"

    # --- Kernel additions (Phase 3) ---------------------------------
    container: "Container" = field(default=None)  # type: ignore[assignment]
    bus: "EventBus" = field(default=None)  # type: ignore[assignment]
    flags: "FeatureFlags" = field(default=None)  # type: ignore[assignment]
    state: "StateMachine" = field(default=None)  # type: ignore[assignment]
    plugin_loader: "PluginLoader | None" = None
    plugin_registry: "PluginRegistry | None" = None

    # --- Phase 4: i18n ----------------------------------------------
    i18n: "I18n | None" = None


def bind_context(client: "Client", ctx: HandlerContext) -> None:
    client._ctx = ctx  # type: ignore[attr-defined]


def get_context(client: "Client") -> HandlerContext:
    ctx: HandlerContext | None = getattr(client, "_ctx", None)
    if ctx is None:
        raise RuntimeError("HandlerContext not bound to client; call bind_context first.")
    return ctx

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
