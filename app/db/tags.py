from __future__ import annotations

import re
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.constants import TAG_NAME_REGEX
from app.utils.time import utcnow

_TAG_RE = re.compile(TAG_NAME_REGEX)


def valid_name(name: str) -> bool:
    return bool(_TAG_RE.match(name))


async def create(
    db: AsyncIOMotorDatabase,
    *,
    name: str,
    created_by: int,
    emoji: str = "",
    description: str = "",
) -> ObjectId | None:
    if not valid_name(name):
        return None
    existing = await db.tags.find_one({"name": name})
    if existing:
        return existing["_id"]
    result = await db.tags.insert_one(
        {
            "name": name,
            "emoji": emoji,
            "description": description,
            "created_by": created_by,
            "created_at": utcnow(),
        }
    )
    return result.inserted_id


async def delete(db: AsyncIOMotorDatabase, name: str) -> bool:
    result = await db.tags.delete_one({"name": name})
    # Also pull the tag from any tickets that have it
    await db.tickets.update_many({"tags": name}, {"$pull": {"tags": name}})
    return result.deleted_count == 1


async def list_all(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    cursor = db.tags.find().sort("name", 1)
    return [doc async for doc in cursor]
