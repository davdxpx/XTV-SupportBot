"""Knowledge-base repository.

Stored in ``kb_articles`` with a compound MongoDB text index on
``title / body / tags`` (weights 10 / 3 / 5) created by
:mod:`xtv_support.infrastructure.db.migrations`.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from xtv_support.domain.models.kb import KbArticle
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover — type-only
    from motor.motor_asyncio import AsyncIOMotorDatabase

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class InvalidSlugError(ValueError):
    """Raised when a slug violates the naming contract."""


def validate_slug(slug: str) -> str:
    if not _SLUG_RE.match(slug or ""):
        raise InvalidSlugError(
            f"Slug must match [a-z0-9][a-z0-9_-]{{0,63}}, got {slug!r}"
        )
    return slug


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------
async def create(
    db: "AsyncIOMotorDatabase",
    *,
    slug: str,
    title: str,
    body: str,
    lang: str = "en",
    tags: list[str] | None = None,
    project_ids: list[str] | None = None,
    created_by: int,
) -> KbArticle:
    validate_slug(slug)
    if await db.kb_articles.find_one({"slug": slug}) is not None:
        raise ValueError(f"KB article {slug!r} already exists.")
    doc: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "body": body,
        "lang": lang,
        "tags": list(tags or []),
        "project_ids": list(project_ids or []),
        "views": 0,
        "helpful": 0,
        "not_helpful": 0,
        "created_by": created_by,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    result = await db.kb_articles.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _from_doc(doc)


async def get_by_slug(
    db: "AsyncIOMotorDatabase", slug: str
) -> KbArticle | None:
    doc = await db.kb_articles.find_one({"slug": slug})
    return _from_doc(doc) if doc else None


async def get_by_id(
    db: "AsyncIOMotorDatabase", article_id: str
) -> KbArticle | None:
    from bson import ObjectId

    doc = await db.kb_articles.find_one({"_id": ObjectId(article_id)})
    return _from_doc(doc) if doc else None


async def list_all(
    db: "AsyncIOMotorDatabase",
    *,
    lang: str | None = None,
    project_id: str | None = None,
    limit: int = 100,
) -> list[KbArticle]:
    query: dict[str, Any] = {}
    if lang is not None:
        query["lang"] = lang
    if project_id is not None:
        query["project_ids"] = project_id
    cursor = db.kb_articles.find(query).sort("updated_at", -1).limit(limit)
    return [_from_doc(d) async for d in cursor]


async def update(
    db: "AsyncIOMotorDatabase",
    slug: str,
    *,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
    lang: str | None = None,
    project_ids: list[str] | None = None,
) -> bool:
    update_set: dict[str, Any] = {"updated_at": utcnow()}
    if title is not None:
        update_set["title"] = title
    if body is not None:
        update_set["body"] = body
    if tags is not None:
        update_set["tags"] = list(tags)
    if lang is not None:
        update_set["lang"] = lang
    if project_ids is not None:
        update_set["project_ids"] = list(project_ids)
    result = await db.kb_articles.update_one({"slug": slug}, {"$set": update_set})
    return result.matched_count == 1


async def delete(db: "AsyncIOMotorDatabase", slug: str) -> bool:
    result = await db.kb_articles.delete_one({"slug": slug})
    return result.deleted_count == 1


# ----------------------------------------------------------------------
# Search + counters
# ----------------------------------------------------------------------
async def search(
    db: "AsyncIOMotorDatabase",
    query: str,
    *,
    lang: str | None = None,
    project_id: str | None = None,
    limit: int = 5,
) -> list[KbArticle]:
    """Run a full-text search and return articles ordered by relevance.

    Optional filters: ``lang`` restricts to that locale, ``project_id``
    restricts to articles scoped to that project (``project_ids == []``
    means unscoped / visible everywhere).
    """
    if not query or not query.strip():
        return []

    filter_: dict[str, Any] = {"$text": {"$search": query}}
    if lang is not None:
        filter_["lang"] = lang
    if project_id is not None:
        filter_["$or"] = [
            {"project_ids": project_id},
            {"project_ids": {"$size": 0}},
        ]

    projection = {"score": {"$meta": "textScore"}}
    cursor = (
        db.kb_articles.find(filter_, projection=projection)
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )
    return [_from_doc(d) async for d in cursor]


async def increment_views(db: "AsyncIOMotorDatabase", slug: str) -> None:
    await db.kb_articles.update_one({"slug": slug}, {"$inc": {"views": 1}})


async def record_feedback(
    db: "AsyncIOMotorDatabase", slug: str, *, helpful: bool
) -> None:
    field = "helpful" if helpful else "not_helpful"
    await db.kb_articles.update_one({"slug": slug}, {"$inc": {field: 1}})


def _from_doc(doc: dict[str, Any]) -> KbArticle:
    return KbArticle(
        id=str(doc.get("_id")),
        slug=str(doc["slug"]),
        title=str(doc.get("title") or ""),
        body=str(doc.get("body") or ""),
        lang=str(doc.get("lang") or "en"),
        tags=tuple(doc.get("tags") or ()),
        project_ids=tuple(str(p) for p in (doc.get("project_ids") or ())),
        views=int(doc.get("views") or 0),
        helpful=int(doc.get("helpful") or 0),
        not_helpful=int(doc.get("not_helpful") or 0),
        created_by=doc.get("created_by"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )
