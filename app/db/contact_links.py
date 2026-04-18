from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.time import utcnow


async def create(
    db: AsyncIOMotorDatabase,
    *,
    admin_id: int,
    display_name: str,
    is_anonymous: bool,
) -> str:
    link_uuid = str(uuid_mod.uuid4())
    await db.contact_links.insert_one(
        {
            "uuid": link_uuid,
            "admin_id": admin_id,
            "display_name": display_name,
            "is_anonymous": is_anonymous,
            "created_at": utcnow(),
        }
    )
    return link_uuid


async def get(db: AsyncIOMotorDatabase, link_uuid: str) -> dict[str, Any] | None:
    return await db.contact_links.find_one({"uuid": link_uuid})
