from __future__ import annotations

from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client

from xtv_support.config.runtime import get_runtime
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import tickets as tickets_repo
from xtv_support.services.tickets import topic_service

log = get_logger("task.topic_cleanup")


async def run_once(client: Client, db: AsyncIOMotorDatabase) -> int:
    """Delete forum topics of tickets closed longer than the configured delay.

    Reads the delay live (runtime settings), so a no-op when
    ``TOPIC_DELETE_AFTER_CLOSE_MINUTES`` is 0 (feature disabled). Returns the
    number of topics deleted.
    """
    rt = await get_runtime(db)
    minutes = rt.TOPIC_DELETE_AFTER_CLOSE_MINUTES
    if minutes <= 0:
        return 0
    stale = await tickets_repo.find_closed_topics_before(db, threshold=timedelta(minutes=minutes))
    deleted = 0
    for ticket in stale:
        topic_id = ticket.get("topic_id")
        if not topic_id:
            continue
        if await topic_service.delete_topic(client, topic_id):
            await tickets_repo.clear_topic(db, ticket["_id"])
            deleted += 1
    if deleted:
        log.info("topic_cleanup.deleted", count=deleted)
    return deleted


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
