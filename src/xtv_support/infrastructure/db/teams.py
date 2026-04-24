"""Team repository.

``_id`` is the team slug (``support-tier1``), so membership lookups and
queue routing use natural keys without an extra join collection.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from xtv_support.domain.enums import Weekday
from xtv_support.domain.models.team import BusinessHoursWindow, QueueRule, Team
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover — type-only
    from motor.motor_asyncio import AsyncIOMotorDatabase

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class InvalidSlugError(ValueError):
    """Raised when a team id violates the slug contract."""


def validate_slug(slug: str) -> str:
    if not _SLUG_RE.match(slug):
        raise InvalidSlugError(f"Team id must match [a-z0-9][a-z0-9_-]{{0,31}}, got {slug!r}")
    return slug


async def create(
    db: AsyncIOMotorDatabase,
    *,
    team_id: str,
    name: str,
    timezone: str = "UTC",
    created_by: int,
) -> Team:
    validate_slug(team_id)
    doc: dict[str, Any] = {
        "_id": team_id,
        "name": name,
        "timezone": timezone,
        "business_hours": [],
        "holidays": [],
        "member_ids": [],
        "queue_rules": [],
        "created_by": created_by,
        "created_at": utcnow(),
    }
    await db.teams.insert_one(doc)
    return _team_from_doc(doc)


async def get(db: AsyncIOMotorDatabase, team_id: str) -> Team | None:
    doc = await db.teams.find_one({"_id": team_id})
    return _team_from_doc(doc) if doc else None


async def list_all(db: AsyncIOMotorDatabase) -> list[Team]:
    return [_team_from_doc(d) async for d in db.teams.find()]


async def list_for_member(db: AsyncIOMotorDatabase, user_id: int) -> list[Team]:
    return [_team_from_doc(d) async for d in db.teams.find({"member_ids": user_id})]


async def delete(db: AsyncIOMotorDatabase, team_id: str) -> bool:
    result = await db.teams.delete_one({"_id": team_id})
    return result.deleted_count == 1


async def rename(db: AsyncIOMotorDatabase, team_id: str, name: str) -> None:
    await db.teams.update_one({"_id": team_id}, {"$set": {"name": name}})


async def set_timezone(db: AsyncIOMotorDatabase, team_id: str, tz: str) -> None:
    await db.teams.update_one({"_id": team_id}, {"$set": {"timezone": tz}})


async def add_member(db: AsyncIOMotorDatabase, team_id: str, user_id: int) -> None:
    await db.teams.update_one({"_id": team_id}, {"$addToSet": {"member_ids": user_id}})


async def remove_member(db: AsyncIOMotorDatabase, team_id: str, user_id: int) -> None:
    await db.teams.update_one({"_id": team_id}, {"$pull": {"member_ids": user_id}})


async def set_business_hours(
    db: AsyncIOMotorDatabase,
    team_id: str,
    windows: list[BusinessHoursWindow],
) -> None:
    payload = [{"weekday": int(w.weekday), "start": w.start, "end": w.end} for w in windows]
    await db.teams.update_one({"_id": team_id}, {"$set": {"business_hours": payload}})


async def set_holidays(db: AsyncIOMotorDatabase, team_id: str, dates: list[str]) -> None:
    await db.teams.update_one({"_id": team_id}, {"$set": {"holidays": list(dates)}})


async def set_queue_rules(
    db: AsyncIOMotorDatabase,
    team_id: str,
    rules: list[QueueRule],
) -> None:
    payload = [{"match": dict(r.match), "weight": int(r.weight)} for r in rules]
    await db.teams.update_one({"_id": team_id}, {"$set": {"queue_rules": payload}})


def _team_from_doc(doc: dict[str, Any]) -> Team:
    hours = tuple(
        BusinessHoursWindow(
            weekday=Weekday(int(h["weekday"])),
            start=str(h["start"]),
            end=str(h["end"]),
        )
        for h in (doc.get("business_hours") or [])
    )
    rules = tuple(
        QueueRule(
            match=dict(r.get("match", {})),
            weight=int(r.get("weight", 100)),
        )
        for r in (doc.get("queue_rules") or [])
    )
    return Team(
        id=str(doc["_id"]),
        name=str(doc.get("name") or doc["_id"]),
        timezone=str(doc.get("timezone") or "UTC"),
        business_hours=hours,
        holidays=tuple(doc.get("holidays") or ()),
        member_ids=tuple(int(m) for m in (doc.get("member_ids") or ())),
        queue_rules=rules,
        created_by=doc.get("created_by"),
        created_at=doc.get("created_at"),
    )
