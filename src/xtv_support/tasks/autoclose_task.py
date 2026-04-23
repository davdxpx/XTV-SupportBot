from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client

from app.core.logger import get_logger
from app.services import autoclose_service

log = get_logger("task.autoclose")


async def run_once(client: Client, db: AsyncIOMotorDatabase) -> None:
    count = await autoclose_service.sweep(client, db)
    if count:
        log.info("autoclose.closed", count=count)

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
