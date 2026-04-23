from __future__ import annotations

from pyrogram import Client
from pyrogram.enums import ParseMode

from xtv_support.config.flags import FeatureFlags, get_flags
from xtv_support.config.i18n import load_locales
from xtv_support.config.settings import settings
from xtv_support.core import i18n as i18n_mod
from xtv_support.core.container import Container
from xtv_support.core.context import HandlerContext
from xtv_support.core.events import EventBus
from xtv_support.core.i18n import I18n
from xtv_support.core.logger import configure_logging, get_logger
from xtv_support.core.state import MemoryStateStore, StateMachine, StateStore
from xtv_support.infrastructure.db import migrations as db_migrations
from xtv_support.infrastructure.db.client import close as close_db
from xtv_support.infrastructure.db.client import get_db
from xtv_support.plugins.loader import PluginLoader
from xtv_support.plugins.registry import PluginRegistry
from xtv_support.services.broadcasts.service import BroadcastManager
from xtv_support.services.cooldown.service import CooldownService
from xtv_support.services.sla.service import SlaService
from xtv_support.tasks.scheduler import TaskManager

log = get_logger("bootstrap")

# Module-level handles kept so the graceful shutdown in `shutdown()` can
# reach the plugin loader without the caller having to pass it around.
_plugin_loader: PluginLoader | None = None


def build_client() -> Client:
    configure_logging()
    app = Client(
        "xtvfeedback_bot",
        api_id=settings.API_ID,
        api_hash=settings.API_HASH.get_secret_value(),
        bot_token=settings.BOT_TOKEN.get_secret_value(),
        parse_mode=ParseMode.HTML,
        # Handlers are registered explicitly from xtv_support.core.router.register_all
        # after the client is created and the HandlerContext is bound.
    )
    return app


async def build_context(client: Client) -> HandlerContext:
    global _plugin_loader

    db = get_db()
    await db_migrations.run(db)

    # --- Classic services (unchanged) -------------------------------
    tasks = TaskManager()
    cooldown = CooldownService()
    sla = SlaService(client, db)
    broadcasts = BroadcastManager(client, db)

    # --- Kernel (Phase 3) -------------------------------------------
    container = Container()
    bus = EventBus()
    flags = get_flags()
    state_store: StateStore = MemoryStateStore()
    state_machine = StateMachine(state_store)
    registry = PluginRegistry()

    # --- i18n (Phase 4) ---------------------------------------------
    i18n_locales = load_locales()
    i18n = I18n(locales=i18n_locales, default_lang=settings.DEFAULT_LANG)
    i18n_mod.set_instance(i18n)
    log.info(
        "i18n.loaded",
        supported=i18n.supported(),
        default=i18n.default_lang,
    )

    # Register every singleton the rest of the app may want to resolve.
    container.register_instance(Client, client)
    container.register_instance(EventBus, bus)
    container.register_instance(FeatureFlags, flags)
    container.register_instance(StateMachine, state_machine)
    container.register_instance(I18n, i18n)
    container.register_instance(TaskManager, tasks)
    container.register_instance(CooldownService, cooldown)
    container.register_instance(SlaService, sla)
    container.register_instance(BroadcastManager, broadcasts)

    # --- Plugins ----------------------------------------------------
    loader = PluginLoader(container=container, bus=bus, flags=flags, registry=registry)
    await loader.load_all()
    _plugin_loader = loader

    ctx = HandlerContext(
        client=client,
        settings=settings,
        db=db,
        tasks=tasks,
        cooldown=cooldown,
        sla=sla,
        broadcasts=broadcasts,
        container=container,
        bus=bus,
        flags=flags,
        state=state_machine,
        plugin_loader=loader,
        plugin_registry=registry,
        i18n=i18n,
    )
    log.info(
        "bootstrap.ready",
        plugins_loaded=len(registry.loaded()),
        plugins_failed=len(registry.failed()),
        plugins_disabled=len(registry.disabled()),
        container_keys=len(container.keys()),
    )
    return ctx


async def shutdown() -> None:
    global _plugin_loader
    if _plugin_loader is not None:
        try:
            await _plugin_loader.unload_all()
        except Exception as exc:  # noqa: BLE001
            log.warning("shutdown.plugin_unload_failed", error=str(exc))
        _plugin_loader = None
    i18n_mod.reset_instance()
    await close_db()


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
