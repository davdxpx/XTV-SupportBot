"""Ticket write endpoints — all dispatched through ActionExecutor.

Using the shared executor means API-driven writes emit the same
``ActionExecuted`` / ``ActionFailed`` events as bot-UI writes, and go
through identical validation. No parallel code path.

Scope: every route below requires ``tickets:write``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel, Field

    from xtv_support.api.deps import get_db, require_scope
    from xtv_support.core.events import EventBus
    from xtv_support.services.actions import ActionContext, ActionExecutor, default_registry

    router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])

    class ClosePayload(BaseModel):
        reason: str = Field(default="resolved", max_length=80)

    class ReopenPayload(BaseModel):
        reason: str | None = None

    class AssignPayload(BaseModel):
        assignee_id: int | None = None

    class TagsPayload(BaseModel):
        tags: list[str]

    class PriorityPayload(BaseModel):
        priority: str  # low | normal | high

    class NotePayload(BaseModel):
        text: str

    class BulkActionPayload(BaseModel):
        action: str
        params: dict = Field(default_factory=dict)

    async def _run(
        *,
        db,
        name: str,
        ticket_id: str,
        params: dict,
        actor_id: int | None,
    ) -> dict:
        executor = ActionExecutor(registry=default_registry)
        # The API doesn't hold a pyrofork client — actions that need one
        # (currently none of the built-ins; "reply" is scaffolded for a
        # follow-up once the topic service exposes an origin-agnostic
        # helper) raise gracefully via ``ticket_required`` / detail.
        bus: EventBus = EventBus()  # ephemeral for per-request audit
        ctx = ActionContext(db=db, bus=bus, actor_id=actor_id, origin="api")
        result = await executor.execute(ctx, name, ticket_id=ticket_id, params=params)
        if not result.ok:
            raise HTTPException(status_code=400, detail=result.detail or "action_failed")
        return {"ok": True, "action": name, "data": result.data}

    @router.post("/{ticket_id}/close")
    async def close_ticket(
        ticket_id: str,
        body: ClosePayload,
        db=Depends(get_db),
        key=Depends(require_scope("tickets:write")),
    ) -> dict:
        return await _run(
            db=db,
            name="close",
            ticket_id=ticket_id,
            params={"reason": body.reason},
            actor_id=key.created_by,
        )

    @router.post("/{ticket_id}/reopen")
    async def reopen_ticket(
        ticket_id: str,
        body: ReopenPayload,
        db=Depends(get_db),
        key=Depends(require_scope("tickets:write")),
    ) -> dict:
        return await _run(
            db=db,
            name="reopen",
            ticket_id=ticket_id,
            params={"reason": body.reason} if body.reason else {},
            actor_id=key.created_by,
        )

    @router.post("/{ticket_id}/assign")
    async def assign_ticket(
        ticket_id: str,
        body: AssignPayload,
        db=Depends(get_db),
        key=Depends(require_scope("tickets:write")),
    ) -> dict:
        return await _run(
            db=db,
            name="assign",
            ticket_id=ticket_id,
            params={"assignee_id": body.assignee_id},
            actor_id=key.created_by,
        )

    @router.post("/{ticket_id}/tags")
    async def set_tags(
        ticket_id: str,
        body: TagsPayload,
        db=Depends(get_db),
        key=Depends(require_scope("tickets:write")),
    ) -> dict:
        # Replacement semantics: compute diff and emit individual tag/untag
        # so every change goes through ActionExecutor consistently.
        from bson import ObjectId

        try:
            oid = ObjectId(ticket_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"bad_id: {exc}") from exc
        current = (await db.tickets.find_one({"_id": oid}, projection={"tags": 1})) or {}
        existing = set(current.get("tags") or [])
        wanted = set(body.tags)
        added = wanted - existing
        removed = existing - wanted
        for tag in added:
            await _run(
                db=db,
                name="tag",
                ticket_id=ticket_id,
                params={"tag": tag},
                actor_id=key.created_by,
            )
        for tag in removed:
            await _run(
                db=db,
                name="untag",
                ticket_id=ticket_id,
                params={"tag": tag},
                actor_id=key.created_by,
            )
        return {"ok": True, "added": sorted(added), "removed": sorted(removed)}

    @router.post("/{ticket_id}/priority")
    async def set_priority(
        ticket_id: str,
        body: PriorityPayload,
        db=Depends(get_db),
        key=Depends(require_scope("tickets:write")),
    ) -> dict:
        return await _run(
            db=db,
            name="set_priority",
            ticket_id=ticket_id,
            params={"priority": body.priority},
            actor_id=key.created_by,
        )

    @router.post("/{ticket_id}/notes")
    async def add_note(
        ticket_id: str,
        body: NotePayload,
        db=Depends(get_db),
        key=Depends(require_scope("tickets:write")),
    ) -> dict:
        return await _run(
            db=db,
            name="add_internal_note",
            ticket_id=ticket_id,
            params={"text": body.text},
            actor_id=key.created_by,
        )

    @router.post("/{ticket_id}/bulk-action")
    async def bulk_action(
        ticket_id: str,
        body: BulkActionPayload,
        db=Depends(get_db),
        key=Depends(require_scope("tickets:write")),
    ) -> dict:
        return await _run(
            db=db,
            name=body.action,
            ticket_id=ticket_id,
            params=body.params or {},
            actor_id=key.created_by,
        )

    return router
