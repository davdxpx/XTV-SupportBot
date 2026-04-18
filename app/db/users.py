from __future__ import annotations

from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.time import utcnow


async def touch(
    db: AsyncIOMotorDatabase,
    *,
    user_id: int,
    first_name: str | None = None,
    username: str | None = None,
) -> None:
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "first_name": first_name or "",
                "username": username,
                "last_seen": utcnow(),
            }
        },
        upsert=True,
    )


async def get(db: AsyncIOMotorDatabase, user_id: int) -> dict[str, Any] | None:
    return await db.users.find_one({"user_id": user_id})


async def set_state(
    db: AsyncIOMotorDatabase,
    user_id: int,
    state: str,
    data: dict[str, Any] | None = None,
) -> None:
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"state": state, "data": data or {}, "updated_at": utcnow()}},
        upsert=True,
    )


async def clear_state(db: AsyncIOMotorDatabase, user_id: int) -> None:
    await db.users.update_one({"user_id": user_id}, {"$unset": {"state": "", "data": ""}})


async def patch_state_data(db: AsyncIOMotorDatabase, user_id: int, patch: dict[str, Any]) -> None:
    mongo_patch = {f"data.{k}": v for k, v in patch.items()}
    await db.users.update_one({"user_id": user_id}, {"$set": mongo_patch})


async def block(db: AsyncIOMotorDatabase, user_id: int) -> None:
    await db.users.update_one({"user_id": user_id}, {"$set": {"blocked": True}}, upsert=True)


async def unblock(db: AsyncIOMotorDatabase, user_id: int) -> None:
    await db.users.update_one({"user_id": user_id}, {"$set": {"blocked": False}})


async def is_blocked(db: AsyncIOMotorDatabase, user_id: int) -> bool:
    doc = await db.users.find_one({"user_id": user_id}, projection={"blocked": 1})
    return bool(doc and doc.get("blocked"))


async def set_cooldown(
    db: AsyncIOMotorDatabase, user_id: int, *, until: datetime | None
) -> None:
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"cooldown_until": until}},
        upsert=True,
    )


async def get_cooldown(db: AsyncIOMotorDatabase, user_id: int) -> datetime | None:
    doc = await db.users.find_one({"user_id": user_id}, projection={"cooldown_until": 1})
    return (doc or {}).get("cooldown_until")


async def get_tickets_seen_at(db: AsyncIOMotorDatabase, user_id: int) -> datetime | None:
    doc = await db.users.find_one({"user_id": user_id}, projection={"tickets_seen_at": 1})
    return (doc or {}).get("tickets_seen_at")


async def mark_tickets_seen(db: AsyncIOMotorDatabase, user_id: int) -> None:
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"tickets_seen_at": utcnow()}},
        upsert=True,
    )


async def count(db: AsyncIOMotorDatabase, *, blocked: bool | None = None) -> int:
    query: dict[str, Any] = {}
    if blocked is True:
        query["blocked"] = True
    elif blocked is False:
        query["$or"] = [{"blocked": {"$ne": True}}, {"blocked": {"$exists": False}}]
    return await db.users.count_documents(query)


async def iter_active(
    db: AsyncIOMotorDatabase, *, batch_size: int = 500
) -> "list[dict[str, Any]]":
    """Return active users' ids. Used by broadcast."""
    cursor = db.users.find(
        {"$or": [{"blocked": {"$ne": True}}, {"blocked": {"$exists": False}}]},
        projection={"user_id": 1},
        batch_size=batch_size,
    )
    return [doc async for doc in cursor]

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
