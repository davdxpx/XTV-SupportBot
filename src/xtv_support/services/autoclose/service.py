from __future__ import annotations

from datetime import timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client

from xtv_support.config.settings import settings
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.services.tickets import topic_service
from xtv_support.ui.primitives.card import send_card
from xtv_support.ui.templates import user_messages
from xtv_support.utils.ids import short_ticket_id

log = get_logger("autoclose")


async def sweep(client: Client, db: AsyncIOMotorDatabase) -> int:
    threshold = timedelta(days=settings.AUTO_CLOSE_DAYS)
    stale = await tickets_repo.find_stale(db, threshold=threshold)
    if not stale:
        return 0
    closed = 0
    for ticket in stale:
        try:
            await _close_one(client, db, ticket)
            closed += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("autoclose.failed", ticket=str(ticket["_id"]), error=str(exc))
    log.info("autoclose.sweep", closed=closed)
    return closed


async def _close_one(client: Client, db: AsyncIOMotorDatabase, ticket: dict[str, Any]) -> None:
    short = short_ticket_id(ticket["_id"])
    await tickets_repo.close(db, ticket["_id"], closed_by=None, reason="auto_inactive")
    topic_id = ticket.get("topic_id")
    if topic_id:
        await topic_service.close_topic(client, topic_id)
    try:
        await send_card(
            client,
            ticket["user_id"],
            user_messages.auto_closed_card(short, settings.AUTO_CLOSE_DAYS),
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("autoclose.notify_failed", user_id=ticket["user_id"], error=str(exc))


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
