from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.time import utcnow


async def log(
    db: AsyncIOMotorDatabase,
    *,
    actor_id: int,
    action: str,
    target_type: str = "",
    target_id: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    await db.audit_log.insert_one(
        {
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "payload": payload or {},
            "ts": utcnow(),
        }
    )
