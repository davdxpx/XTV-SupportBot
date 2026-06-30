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
    from fastapi import APIRouter, Depends, HTTPException, Query, Request

    from xtv_support.api.deps import get_db, require_scope
    from xtv_support.services.external_directory.model import DirectoryProviderLike

    router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])

    @router.get("")
    async def list_tickets(
        request: Request,
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
        provider = request.app.state.container.resolve(DirectoryProviderLike)
        rows = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if "project_id" in doc and doc["project_id"] is not None:
                doc["project_id"] = str(doc["project_id"])
            if "team_id" in doc and doc["team_id"] is not None:
                doc["team_id"] = str(doc["team_id"])

            signal = await provider.get_signal(doc["user_id"])
            if signal.is_vip or signal.display_badge or signal.tier_label:
                doc["is_vip"] = signal.is_vip
                doc["tier_label"] = signal.tier_label
                doc["display_badge"] = signal.display_badge

            rows.append(doc)
        return {"items": rows, "count": len(rows)}

    @router.get("/stats")
    async def ticket_stats(
        db=Depends(get_db),
        _key=Depends(require_scope("tickets:read")),
    ) -> dict:
        # Live counts straight from the tickets collection — independent of the
        # nightly analytics_daily rollup, so the console is never stuck at 0.
        from xtv_support.infrastructure.db import tickets as tickets_repo

        return await tickets_repo.stats(db)

    @router.get("/{ticket_id}/attachments/{index}")
    async def get_attachment(
        request: Request,
        ticket_id: str,
        index: int,
        db=Depends(get_db),
        _key=Depends(require_scope("tickets:read")),
    ):
        from fastapi import Response
        from pyrogram import Client

        from xtv_support.infrastructure.db import tickets as tickets_repo
        from xtv_support.services.tickets import service as ticket_service

        doc = await tickets_repo.get(db, ticket_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="not_found")
        container = getattr(request.app.state, "container", None)
        client = container.resolve(Client) if container is not None else None
        if client is None:
            raise HTTPException(status_code=503, detail="attachments_unavailable")
        result = await ticket_service.download_attachment(client, doc, index)
        if result is None:
            raise HTTPException(status_code=404, detail="attachment_not_found")
        data, mime = result
        return Response(content=data, media_type=mime)

    @router.get("/{ticket_id}")
    async def get_ticket(
        request: Request,
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
        if "project_id" in doc and doc["project_id"] is not None:
            doc["project_id"] = str(doc["project_id"])
        if "team_id" in doc and doc["team_id"] is not None:
            doc["team_id"] = str(doc["team_id"])

        provider = request.app.state.container.resolve(DirectoryProviderLike)
        signal = await provider.get_signal(doc["user_id"])
        if signal.is_vip or signal.display_badge or signal.tier_label:
            doc["is_vip"] = signal.is_vip
            doc["tier_label"] = signal.tier_label
            doc["display_badge"] = signal.display_badge

        return doc

    return router
