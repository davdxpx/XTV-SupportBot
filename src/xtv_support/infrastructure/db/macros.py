"""Macros repository.

Stored in the ``macros`` collection with indexes created in
:mod:`xtv_support.infrastructure.db.migrations`::

    {_id, name, team_id|null, body, tags, usage_count,
     created_by, created_at, updated_at}
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from xtv_support.domain.models.macro import Macro
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover — type-only
    from motor.motor_asyncio import AsyncIOMotorDatabase

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class InvalidMacroNameError(ValueError):
    """Raised when a macro name violates the naming contract."""


def validate_name(name: str) -> str:
    if not _NAME_RE.match(name or ""):
        raise InvalidMacroNameError(
            f"Macro name must match [a-z0-9][a-z0-9_-]{{0,31}}, got {name!r}"
        )
    return name


async def create(
    db: AsyncIOMotorDatabase,
    *,
    name: str,
    body: str,
    team_id: str | None = None,
    tags: list[str] | None = None,
    created_by: int,
) -> Macro:
    validate_name(name)
    existing = await db.macros.find_one({"name": name, "team_id": team_id})
    if existing is not None:
        raise ValueError(
            f"Macro {name!r} already exists for "
            f"{('team=' + team_id) if team_id else 'global scope'}."
        )
    doc: dict[str, Any] = {
        "name": name,
        "body": body,
        "team_id": team_id,
        "tags": list(tags or []),
        "usage_count": 0,
        "created_by": created_by,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    result = await db.macros.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _macro_from_doc(doc)


async def get_by_name(
    db: AsyncIOMotorDatabase,
    name: str,
    *,
    team_id: str | None = None,
) -> Macro | None:
    """Return a macro visible to ``team_id``.

    Lookup order when ``team_id`` is provided:
    1. Team-specific macro (``team_id == team_id``)
    2. Global macro (``team_id is None``)

    Passing ``team_id=None`` only matches global macros.
    """
    if team_id is not None:
        doc = await db.macros.find_one({"name": name, "team_id": team_id})
        if doc is not None:
            return _macro_from_doc(doc)
    doc = await db.macros.find_one({"name": name, "team_id": None})
    return _macro_from_doc(doc) if doc else None


async def list_visible(
    db: AsyncIOMotorDatabase,
    *,
    team_id: str | None = None,
) -> list[Macro]:
    """Every macro an agent of ``team_id`` can see: team + global."""
    query: dict[str, Any]
    if team_id is None:
        query = {"team_id": None}
    else:
        query = {"$or": [{"team_id": None}, {"team_id": team_id}]}
    cursor = db.macros.find(query).sort("name", 1)
    return [_macro_from_doc(d) async for d in cursor]


async def update_body(
    db: AsyncIOMotorDatabase,
    macro_id: str,
    body: str,
) -> None:
    from bson import ObjectId

    await db.macros.update_one(
        {"_id": ObjectId(macro_id)},
        {"$set": {"body": body, "updated_at": utcnow()}},
    )


async def delete(db: AsyncIOMotorDatabase, macro_id: str) -> bool:
    from bson import ObjectId

    result = await db.macros.delete_one({"_id": ObjectId(macro_id)})
    return result.deleted_count == 1


async def increment_usage(db: AsyncIOMotorDatabase, macro_id: str) -> None:
    from bson import ObjectId

    await db.macros.update_one({"_id": ObjectId(macro_id)}, {"$inc": {"usage_count": 1}})


def _macro_from_doc(doc: dict[str, Any]) -> Macro:
    return Macro(
        id=str(doc.get("_id")),
        name=str(doc["name"]),
        body=str(doc.get("body") or ""),
        team_id=(doc.get("team_id") or None),
        tags=tuple(doc.get("tags") or ()),
        usage_count=int(doc.get("usage_count") or 0),
        created_by=doc.get("created_by"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )
