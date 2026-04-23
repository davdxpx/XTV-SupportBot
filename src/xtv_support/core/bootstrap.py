from __future__ import annotations

from pyrogram import Client
from pyrogram.enums import ParseMode

from xtv_support.config.settings import settings
from xtv_support.core.context import HandlerContext
from xtv_support.core.logger import configure_logging, get_logger
from xtv_support.infrastructure.db import migrations as db_migrations
from xtv_support.infrastructure.db.client import close as close_db
from xtv_support.infrastructure.db.client import get_db
from xtv_support.services.broadcasts.service import BroadcastManager
from xtv_support.services.cooldown.service import CooldownService
from xtv_support.services.sla.service import SlaService
from xtv_support.tasks.scheduler import TaskManager

log = get_logger("bootstrap")


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
    db = get_db()
    await db_migrations.run(db)
    tasks = TaskManager()
    cooldown = CooldownService()
    sla = SlaService(client, db)
    broadcasts = BroadcastManager(client, db)
    return HandlerContext(
        client=client,
        settings=settings,
        db=db,
        tasks=tasks,
        cooldown=cooldown,
        sla=sla,
        broadcasts=broadcasts,
    )


async def shutdown() -> None:
    await close_db()

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
