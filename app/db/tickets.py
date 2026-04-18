from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.ids import safe_objectid
from app.utils.time import utcnow


async def create(
    db: AsyncIOMotorDatabase,
    *,
    project_id: str | ObjectId | None,
    user_id: int,
    message: str,
    message_type: str = "text",
    file_id: str | None = None,
    contact_uuid: str | None = None,
    priority: str = "normal",
    sla_deadline: datetime | None = None,
) -> ObjectId | None:
    p_oid = safe_objectid(project_id) if project_id else None
    now = utcnow()
    doc = {
        "project_id": p_oid,
        "user_id": user_id,
        "contact_uuid": contact_uuid,
        "message": message,
        "type": message_type,
        "file_id": file_id,
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "topic_id": None,
        "topic_fallback": False,
        "header_msg_id": None,
        "history": [
            {
                "sender": "user",
                "text": message,
                "type": message_type,
                "file_id": file_id,
                "timestamp": now,
            }
        ],
        "assignee_id": None,
        "assigned_at": None,
        "assigned_by": None,
        "tags": [],
        "priority": priority,
        "sla_deadline": sla_deadline,
        "sla_warned": False,
        "last_user_msg_at": now,
        "last_admin_msg_at": None,
    }
    result = await db.tickets.insert_one(doc)
    tid = result.inserted_id

    update_user = {
        "$set": {
            "last_ticket_id": tid,
            "last_active_project": str(p_oid) if p_oid else None,
            "last_seen": now,
        }
    }
    await db.users.update_one({"user_id": user_id}, update_user, upsert=True)

    if p_oid:
        await db.projects.update_one({"_id": p_oid}, {"$inc": {"ticket_count": 1}})

    return tid


async def get(db: AsyncIOMotorDatabase, ticket_id: str | ObjectId) -> dict[str, Any] | None:
    oid = ticket_id if isinstance(ticket_id, ObjectId) else safe_objectid(ticket_id)
    if oid is None:
        return None
    return await db.tickets.find_one({"_id": oid})


async def get_by_topic(db: AsyncIOMotorDatabase, topic_id: int) -> dict[str, Any] | None:
    return await db.tickets.find_one({"topic_id": topic_id})


async def get_user_topic(
    db: AsyncIOMotorDatabase, user_id: int, project_id: str | ObjectId | None = None
) -> dict[str, Any] | None:
    query: dict[str, Any] = {
        "user_id": user_id,
        "status": "open",
        "topic_id": {"$ne": None},
    }
    if project_id:
        oid = safe_objectid(project_id)
        if oid:
            query["project_id"] = oid
    return await db.tickets.find_one(query)


async def list_by_user(
    db: AsyncIOMotorDatabase, user_id: int, *, limit: int = 20
) -> list[dict[str, Any]]:
    cursor = db.tickets.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def list_open_by_project(
    db: AsyncIOMotorDatabase, project_id: str | ObjectId, *, limit: int = 25
) -> list[dict[str, Any]]:
    oid = safe_objectid(project_id)
    if oid is None:
        return []
    cursor = (
        db.tickets.find({"project_id": oid, "status": "open"})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def set_topic(
    db: AsyncIOMotorDatabase,
    ticket_id: ObjectId,
    *,
    topic_id: int | None,
    fallback: bool = False,
) -> None:
    await db.tickets.update_one(
        {"_id": ticket_id},
        {"$set": {"topic_id": topic_id, "topic_fallback": fallback}},
    )


async def set_header_msg(
    db: AsyncIOMotorDatabase, ticket_id: ObjectId, header_msg_id: int
) -> None:
    await db.tickets.update_one(
        {"_id": ticket_id}, {"$set": {"header_msg_id": header_msg_id}}
    )


async def append_history(
    db: AsyncIOMotorDatabase,
    ticket_id: ObjectId,
    *,
    sender: str,
    text: str,
    message_type: str = "text",
    file_id: str | None = None,
) -> None:
    now = utcnow()
    entry = {
        "sender": sender,
        "text": text,
        "type": message_type,
        "file_id": file_id,
        "timestamp": now,
    }
    update: dict[str, Any] = {
        "$push": {"history": entry},
        "$set": {"updated_at": now},
    }
    if sender == "user":
        update["$set"]["last_user_msg_at"] = now
    elif sender == "admin":
        update["$set"]["last_admin_msg_at"] = now
        update["$set"]["sla_warned"] = False
    await db.tickets.update_one({"_id": ticket_id}, update)


async def close(
    db: AsyncIOMotorDatabase,
    ticket_id: ObjectId,
    *,
    closed_by: int | None = None,
    reason: str | None = None,
) -> None:
    now = utcnow()
    await db.tickets.update_one(
        {"_id": ticket_id},
        {
            "$set": {
                "status": "closed",
                "closed_at": now,
                "closed_by": closed_by,
                "close_reason": reason,
                "updated_at": now,
            }
        },
    )


async def assign(
    db: AsyncIOMotorDatabase,
    ticket_id: ObjectId,
    *,
    assignee_id: int | None,
    assigned_by: int,
) -> None:
    await db.tickets.update_one(
        {"_id": ticket_id},
        {
            "$set": {
                "assignee_id": assignee_id,
                "assigned_at": utcnow() if assignee_id else None,
                "assigned_by": assigned_by,
            }
        },
    )


async def toggle_tag(db: AsyncIOMotorDatabase, ticket_id: ObjectId, tag: str) -> list[str]:
    """Add tag if missing, remove if present. Returns new tags list."""
    doc = await db.tickets.find_one({"_id": ticket_id}, projection={"tags": 1})
    tags = list((doc or {}).get("tags") or [])
    if tag in tags:
        tags.remove(tag)
    else:
        tags.append(tag)
    await db.tickets.update_one({"_id": ticket_id}, {"$set": {"tags": tags}})
    return tags


async def set_priority(db: AsyncIOMotorDatabase, ticket_id: ObjectId, priority: str) -> None:
    await db.tickets.update_one({"_id": ticket_id}, {"$set": {"priority": priority}})


async def set_sla(
    db: AsyncIOMotorDatabase,
    ticket_id: ObjectId,
    *,
    deadline: datetime | None,
    warned: bool | None = None,
) -> None:
    update: dict[str, Any] = {"sla_deadline": deadline}
    if warned is not None:
        update["sla_warned"] = warned
    await db.tickets.update_one({"_id": ticket_id}, {"$set": update})


async def find_sla_breached(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    now = utcnow()
    cursor = db.tickets.find(
        {
            "status": "open",
            "sla_warned": False,
            "sla_deadline": {"$ne": None, "$lte": now},
        }
    )
    return [doc async for doc in cursor]


async def find_stale(
    db: AsyncIOMotorDatabase, *, threshold: timedelta
) -> list[dict[str, Any]]:
    cutoff = utcnow() - threshold
    cursor = db.tickets.find(
        {
            "status": "open",
            "$and": [
                {
                    "$or": [
                        {"last_user_msg_at": {"$lt": cutoff}},
                        {"last_user_msg_at": {"$exists": False}},
                    ]
                },
                {
                    "$or": [
                        {"last_admin_msg_at": {"$lt": cutoff}},
                        {"last_admin_msg_at": None},
                        {"last_admin_msg_at": {"$exists": False}},
                    ]
                },
            ],
        }
    )
    return [doc async for doc in cursor]
