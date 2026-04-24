"""Who's-online tracker for the admin panel.

Every admin callback / command pings :func:`touch`, which writes a
``last_seen_at`` timestamp to the ``admin_presence`` Mongo collection.
:func:`count_active` returns how many admins were active in the last
``window`` (default 5 minutes) — powering the "active agents" stat
tile on the Overview tab.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase


async def touch(db: AsyncIOMotorDatabase, user_id: int) -> None:
    await db.admin_presence.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "last_seen_at": utcnow()}},
        upsert=True,
    )


async def count_active(
    db: AsyncIOMotorDatabase,
    *,
    window: timedelta = timedelta(minutes=5),
) -> int:
    cutoff = utcnow() - window
    return await db.admin_presence.count_documents({"last_seen_at": {"$gte": cutoff}})


async def list_active(
    db: AsyncIOMotorDatabase,
    *,
    window: timedelta = timedelta(minutes=5),
    limit: int = 20,
) -> list[dict]:
    cutoff = utcnow() - window
    cursor = (
        db.admin_presence.find({"last_seen_at": {"$gte": cutoff}})
        .sort("last_seen_at", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]
