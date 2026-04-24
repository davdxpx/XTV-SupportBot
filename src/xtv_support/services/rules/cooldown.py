"""Per-rule, per-ticket cooldown tracker.

Backed by Mongo (``rule_cooldowns`` collection) so it survives restarts
and single-replica deploys. A Redis-backed variant is a drop-in for
multi-replica scale; the interface below is the stable one rules use.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase


def _key(rule_id: str, ticket_id: str | None) -> str:
    return f"{rule_id}::{ticket_id or '*'}"


async def can_fire(
    db: AsyncIOMotorDatabase,
    *,
    rule_id: str,
    ticket_id: str | None,
    cooldown_s: int,
) -> bool:
    if cooldown_s <= 0:
        return True
    doc = await db.rule_cooldowns.find_one({"_id": _key(rule_id, ticket_id)})
    if doc is None:
        return True
    last: object = doc.get("last_fired_at")
    if last is None:
        return True
    try:
        delta = utcnow() - last  # type: ignore[operator]
    except TypeError:
        return True
    return delta >= timedelta(seconds=cooldown_s)


async def mark_fired(
    db: AsyncIOMotorDatabase,
    *,
    rule_id: str,
    ticket_id: str | None,
) -> None:
    await db.rule_cooldowns.update_one(
        {"_id": _key(rule_id, ticket_id)},
        {"$set": {"last_fired_at": utcnow()}},
        upsert=True,
    )
