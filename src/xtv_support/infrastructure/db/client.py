from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from xtv_support.config.settings import settings
from xtv_support.core.logger import get_logger

log = get_logger("db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGO_URI.get_secret_value(),
            serverSelectionTimeoutMS=10_000,
            tz_aware=True,
        )
        log.info("mongo.connected", db=settings.MONGO_DB_NAME)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[settings.MONGO_DB_NAME]
    return _db


async def close() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        log.info("mongo.closed")
    _client = None
    _db = None


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
