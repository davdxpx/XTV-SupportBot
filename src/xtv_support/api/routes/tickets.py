"""Tickets read endpoints.

Phase 11b ships read-only endpoints. Write endpoints (reply / close)
land later once the Telegram service layer exposes them outside of
pyrofork handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter, Depends, HTTPException, Query

    from xtv_support.api.deps import get_db, require_scope

    router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])

    @router.get("")
    async def list_tickets(
        db=Depends(get_db),
        _key=Depends(require_scope("tickets:read")),
        status: str | None = Query(None),
        team_id: str | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
    ) -> dict:
        query: dict = {}
        if status:
            query["status"] = status
        if team_id:
            query["team_id"] = team_id
        cursor = (
            db.tickets.find(
                query,
                projection={
                    "_id": 1,
                    "user_id": 1,
                    "project_id": 1,
                    "team_id": 1,
                    "status": 1,
                    "priority": 1,
                    "tags": 1,
                    "created_at": 1,
                    "closed_at": 1,
                    "assignee_id": 1,
                },
            )
            .sort("created_at", -1)
            .limit(limit)
        )
        rows = [{**doc, "_id": str(doc["_id"])} async for doc in cursor]
        return {"items": rows, "count": len(rows)}

    @router.get("/{ticket_id}")
    async def get_ticket(
        ticket_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("tickets:read")),
    ) -> dict:
        from bson import ObjectId

        try:
            oid = ObjectId(ticket_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"bad_id: {exc}") from exc
        doc = await db.tickets.find_one({"_id": oid})
        if doc is None:
            raise HTTPException(status_code=404, detail="not_found")
        doc["_id"] = str(doc["_id"])
        return doc

    return router
