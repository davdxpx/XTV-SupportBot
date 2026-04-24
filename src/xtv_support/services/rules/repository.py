"""``automation_rules`` collection repository.

Rules are stored as plain dicts; :func:`to_rule` converts a fetched
document into the frozen :class:`Rule` dataclass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xtv_support.services.rules.model import ActionRef, Condition, Rule
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase


def _to_rule(doc: dict) -> Rule:
    return Rule(
        id=str(doc.get("_id")),
        name=str(doc.get("name") or ""),
        enabled=bool(doc.get("enabled", False)),
        trigger=str(doc.get("trigger") or ""),
        conditions=tuple(
            Condition(field=c["field"], op=c["op"], value=c["value"])
            for c in (doc.get("conditions") or [])
        ),
        actions=tuple(
            ActionRef(name=a["name"], params=a.get("params") or {})
            for a in (doc.get("actions") or [])
        ),
        cooldown_s=int(doc.get("cooldown_s", 0)),
        max_fires_per_day=doc.get("max_fires_per_day"),
        version=int(doc.get("version", 1)),
        created_by=doc.get("created_by"),
    )


async def create_rule(
    db: AsyncIOMotorDatabase,
    *,
    name: str,
    trigger: str,
    conditions: list[dict] | None = None,
    actions: list[dict] | None = None,
    cooldown_s: int = 0,
    created_by: int | None = None,
    enabled: bool = False,
) -> Rule:
    doc: dict[str, Any] = {
        "name": name,
        "enabled": enabled,
        "trigger": trigger,
        "conditions": conditions or [],
        "actions": actions or [],
        "cooldown_s": cooldown_s,
        "version": 1,
        "created_by": created_by,
        "created_at": utcnow(),
        "history": [],
    }
    result = await db.automation_rules.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_rule(doc)


async def get_rule(db: AsyncIOMotorDatabase, rule_id: str) -> Rule | None:
    from bson import ObjectId

    try:
        oid = ObjectId(rule_id)
    except Exception:  # noqa: BLE001
        return None
    doc = await db.automation_rules.find_one({"_id": oid})
    return _to_rule(doc) if doc else None


async def list_rules(
    db: AsyncIOMotorDatabase,
    *,
    enabled_only: bool = False,
    trigger: str | None = None,
    limit: int = 200,
) -> list[Rule]:
    query: dict[str, Any] = {}
    if enabled_only:
        query["enabled"] = True
    if trigger:
        query["trigger"] = trigger
    cursor = db.automation_rules.find(query).sort("created_at", -1).limit(limit)
    return [_to_rule(doc) async for doc in cursor]


async def enable_rule(db: AsyncIOMotorDatabase, rule_id: str, enabled: bool) -> bool:
    from bson import ObjectId

    try:
        oid = ObjectId(rule_id)
    except Exception:  # noqa: BLE001
        return False
    result = await db.automation_rules.update_one(
        {"_id": oid}, {"$set": {"enabled": enabled, "updated_at": utcnow()}}
    )
    return result.matched_count == 1


async def delete_rule(db: AsyncIOMotorDatabase, rule_id: str) -> bool:
    from bson import ObjectId

    try:
        oid = ObjectId(rule_id)
    except Exception:  # noqa: BLE001
        return False
    result = await db.automation_rules.delete_one({"_id": oid})
    return result.deleted_count == 1
