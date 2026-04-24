"""Projects routes — read only in Phase 11b."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter, Depends, Query

    from xtv_support.api.deps import get_db, require_scope

    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    @router.get("")
    async def list_projects(
        db=Depends(get_db),
        _key=Depends(require_scope("projects:read")),
        active: bool | None = Query(None),
    ) -> dict:
        query: dict = {}
        if active is not None:
            query["active"] = active
        cursor = db.projects.find(query).sort("created_at", -1).limit(200)
        rows: list[dict] = []
        async for doc in cursor:
            doc["_id"] = str(doc.get("_id"))
            rows.append(doc)
        return {"items": rows, "count": len(rows)}

    return router
