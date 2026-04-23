"""GDPR soft-delete + hard-delete sweeper.

Two-step flow:

1. ``request_deletion(user_id)`` — sets ``users.deleted_at`` to the
   current timestamp. The user is blocked from the bot immediately
   and their visible data is scheduled for destruction after a
   grace period (default 30 days) so accidental / coerced requests
   have a chance to be reversed.
2. ``purge_expired(older_than_days)`` — run from a periodic task,
   finds users whose ``deleted_at`` is beyond the grace window and
   drops their tickets + CSAT + audit entries + user doc.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

_log = get_logger("gdpr.delete")

DEFAULT_GRACE_DAYS = 30


@dataclass(frozen=True, slots=True)
class DeletionReceipt:
    user_id: int
    requested_at: datetime
    purge_at: datetime


async def request_deletion(
    db: "AsyncIOMotorDatabase",
    user_id: int,
    *,
    grace_days: int = DEFAULT_GRACE_DAYS,
) -> DeletionReceipt:
    now = utcnow()
    purge_at = now + timedelta(days=grace_days)
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "deleted_at": now,
                "purge_at": purge_at,
                "blocked": True,
            }
        },
        upsert=True,
    )
    _log.info("gdpr.delete.requested", user_id=user_id, purge_at=purge_at.isoformat())
    return DeletionReceipt(user_id=user_id, requested_at=now, purge_at=purge_at)


async def cancel_deletion(db: "AsyncIOMotorDatabase", user_id: int) -> bool:
    """Operators may cancel a pending deletion inside the grace period."""
    result = await db.users.update_one(
        {"user_id": user_id, "deleted_at": {"$ne": None}},
        {
            "$set": {"blocked": False},
            "$unset": {"deleted_at": "", "purge_at": ""},
        },
    )
    if result.modified_count:
        _log.info("gdpr.delete.cancelled", user_id=user_id)
    return result.modified_count == 1


async def purge_expired(
    db: "AsyncIOMotorDatabase",
    *,
    older_than_days: int = DEFAULT_GRACE_DAYS,
) -> int:
    """Hard-delete every user whose grace period has elapsed.

    Returns the number of users purged.
    """
    cutoff = utcnow() - timedelta(days=older_than_days)
    purged = 0
    cursor = db.users.find(
        {"deleted_at": {"$lte": cutoff}},
        projection={"user_id": 1, "_id": 0},
    )
    async for doc in cursor:
        uid = doc.get("user_id")
        if uid is None:
            continue
        try:
            await db.tickets.delete_many({"user_id": uid})
            await db.csat_responses.delete_many({"user_id": uid})
            await db.audit_log.delete_many(
                {"$or": [{"target_id": str(uid)}, {"actor_id": uid}]}
            )
            await db.users.delete_one({"user_id": uid})
            purged += 1
            _log.info("gdpr.purge.one", user_id=uid)
        except Exception as exc:  # noqa: BLE001
            _log.warning("gdpr.purge.failed", user_id=uid, error=str(exc))
    if purged:
        _log.info("gdpr.purge.done", count=purged)
    return purged
