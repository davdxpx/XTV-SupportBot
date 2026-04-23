"""Role-assignment repository.

Stores a single document per user in the ``roles`` collection::

    {user_id, role, team_ids, granted_by, granted_at}

Writers: only the ``owner`` / ``admin`` scope should hit these — the
RBAC middleware enforces that.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xtv_support.domain.enums import Role
from xtv_support.domain.models.role import RoleAssignment
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover — type-only
    from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_role(db: "AsyncIOMotorDatabase", user_id: int) -> RoleAssignment | None:
    doc = await db.roles.find_one({"user_id": user_id})
    if doc is None:
        return None
    return _assignment_from_doc(doc)


async def get_role_or_default(
    db: "AsyncIOMotorDatabase", user_id: int, *, default: Role = Role.USER
) -> RoleAssignment:
    """Return the stored assignment, or a fresh :attr:`USER`-level one."""
    existing = await get_role(db, user_id)
    if existing is not None:
        return existing
    return RoleAssignment(user_id=user_id, role=default)


async def grant(
    db: "AsyncIOMotorDatabase",
    *,
    user_id: int,
    role: Role,
    granted_by: int | None,
    team_ids: list[str] | None = None,
) -> None:
    """Upsert a role. ``team_ids=None`` keeps the existing list."""
    update: dict[str, Any] = {
        "role": str(role),
        "granted_by": granted_by,
        "granted_at": utcnow(),
    }
    if team_ids is not None:
        update["team_ids"] = list(team_ids)
    await db.roles.update_one(
        {"user_id": user_id},
        {"$set": update, "$setOnInsert": {"user_id": user_id}},
        upsert=True,
    )


async def revoke(db: "AsyncIOMotorDatabase", user_id: int) -> None:
    """Delete the role assignment, dropping the user back to :attr:`Role.USER`."""
    await db.roles.delete_one({"user_id": user_id})


async def list_by_role(
    db: "AsyncIOMotorDatabase", role: Role
) -> list[RoleAssignment]:
    cursor = db.roles.find({"role": str(role)})
    return [_assignment_from_doc(doc) async for doc in cursor]


async def list_by_team(
    db: "AsyncIOMotorDatabase", team_id: str
) -> list[RoleAssignment]:
    cursor = db.roles.find({"team_ids": team_id})
    return [_assignment_from_doc(doc) async for doc in cursor]


async def add_to_team(db: "AsyncIOMotorDatabase", user_id: int, team_id: str) -> None:
    await db.roles.update_one(
        {"user_id": user_id},
        {"$addToSet": {"team_ids": team_id}},
    )


async def remove_from_team(db: "AsyncIOMotorDatabase", user_id: int, team_id: str) -> None:
    await db.roles.update_one(
        {"user_id": user_id},
        {"$pull": {"team_ids": team_id}},
    )


def _assignment_from_doc(doc: dict[str, Any]) -> RoleAssignment:
    return RoleAssignment(
        user_id=int(doc["user_id"]),
        role=Role.from_string(doc.get("role")),
        team_ids=tuple(doc.get("team_ids") or ()),
        granted_by=doc.get("granted_by"),
        granted_at=doc.get("granted_at"),
    )
