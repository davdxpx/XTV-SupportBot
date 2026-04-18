from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.time import utcnow


async def create(
    db: AsyncIOMotorDatabase,
    *,
    admin_id: int,
    text: str,
    total: int,
    progress_chat_id: int | None = None,
    progress_msg_id: int | None = None,
) -> ObjectId:
    doc = {
        "admin_id": admin_id,
        "text": text,
        "state": "queued",
        "total": total,
        "sent": 0,
        "failed": 0,
        "blocked_count": 0,
        "started_at": utcnow(),
        "finished_at": None,
        "progress_chat_id": progress_chat_id,
        "progress_msg_id": progress_msg_id,
    }
    result = await db.broadcasts.insert_one(doc)
    return result.inserted_id


async def get(db: AsyncIOMotorDatabase, bid: ObjectId) -> dict[str, Any] | None:
    return await db.broadcasts.find_one({"_id": bid})


async def set_state(
    db: AsyncIOMotorDatabase, bid: ObjectId, state: str, *, finished: bool = False
) -> None:
    update: dict[str, Any] = {"$set": {"state": state}}
    if finished:
        update["$set"]["finished_at"] = utcnow()
    await db.broadcasts.update_one({"_id": bid}, update)


async def increment_counters(
    db: AsyncIOMotorDatabase,
    bid: ObjectId,
    *,
    sent: int = 0,
    failed: int = 0,
    blocked: int = 0,
) -> None:
    inc: dict[str, Any] = {}
    if sent:
        inc["sent"] = sent
    if failed:
        inc["failed"] = failed
    if blocked:
        inc["blocked_count"] = blocked
    if inc:
        await db.broadcasts.update_one({"_id": bid}, {"$inc": inc})


async def find_resumable(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    cursor = db.broadcasts.find({"state": {"$in": ["queued", "running", "paused"]}})
    return [doc async for doc in cursor]


async def find_active(db: AsyncIOMotorDatabase) -> dict[str, Any] | None:
    return await db.broadcasts.find_one({"state": {"$in": ["queued", "running", "paused"]}})


async def set_progress_msg(
    db: AsyncIOMotorDatabase,
    bid: ObjectId,
    *,
    chat_id: int,
    msg_id: int,
    started_at: datetime | None = None,
) -> None:
    update: dict[str, Any] = {
        "$set": {"progress_chat_id": chat_id, "progress_msg_id": msg_id}
    }
    if started_at:
        update["$set"]["started_at"] = started_at
    await db.broadcasts.update_one({"_id": bid}, update)

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
