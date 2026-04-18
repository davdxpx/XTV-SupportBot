from __future__ import annotations

from pyrogram import Client
from pyrogram.enums import ParseMode

from app.config import settings
from app.core.context import HandlerContext
from app.core.logger import configure_logging, get_logger
from app.db import migrations as db_migrations
from app.db.client import close as close_db
from app.db.client import get_db
from app.services.broadcast_service import BroadcastManager
from app.services.cooldown_service import CooldownService
from app.services.sla_service import SlaService
from app.tasks.scheduler import TaskManager

log = get_logger("bootstrap")


def build_client() -> Client:
    configure_logging()
    app = Client(
        "xtvfeedback_bot",
        api_id=settings.API_ID,
        api_hash=settings.API_HASH.get_secret_value(),
        bot_token=settings.BOT_TOKEN.get_secret_value(),
        parse_mode=ParseMode.HTML,
        # Handlers are registered explicitly from app.core.router.register_all
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
