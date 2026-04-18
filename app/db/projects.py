from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.ids import safe_objectid
from app.utils.time import utcnow


async def create(
    db: AsyncIOMotorDatabase,
    *,
    name: str,
    description: str,
    created_by: int,
    project_type: str = "support",
    feedback_topic_id: int | None = None,
    has_rating: bool = False,
    has_text: bool = True,
) -> ObjectId:
    doc = {
        "name": name,
        "description": description,
        "type": project_type,
        "feedback_topic_id": feedback_topic_id,
        "has_rating": has_rating,
        "has_text": has_text,
        "active": True,
        "created_by": created_by,
        "created_at": utcnow(),
        "ticket_count": 0,
    }
    result = await db.projects.insert_one(doc)
    return result.inserted_id


async def get(db: AsyncIOMotorDatabase, project_id: str | ObjectId) -> dict[str, Any] | None:
    oid = safe_objectid(project_id)
    if oid is None:
        return None
    return await db.projects.find_one({"_id": oid})


async def list_all(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    cursor = db.projects.find().sort("created_at", -1)
    return [doc async for doc in cursor]


async def list_active(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    cursor = db.projects.find({"active": True}).sort("created_at", -1)
    return [doc async for doc in cursor]


async def delete(db: AsyncIOMotorDatabase, project_id: str | ObjectId) -> bool:
    oid = safe_objectid(project_id)
    if oid is None:
        return False
    result = await db.projects.delete_one({"_id": oid})
    return result.deleted_count == 1


async def increment_ticket_count(db: AsyncIOMotorDatabase, project_id: ObjectId) -> None:
    await db.projects.update_one({"_id": project_id}, {"$inc": {"ticket_count": 1}})


async def set_active(
    db: AsyncIOMotorDatabase,
    project_id: str | ObjectId,
    *,
    active: bool,
) -> bool:
    oid = safe_objectid(project_id)
    if oid is None:
        return False
    result = await db.projects.update_one({"_id": oid}, {"$set": {"active": active}})
    return result.matched_count == 1
