"""Webhook subscription CRUD.

Webhook subscriptions live in the ``webhook_subscriptions`` Mongo
collection. Secrets are generated server-side, shown once on create,
hashed at rest — same shape as the API-key model.

Events are the values of :data:`KNOWN_EVENTS`. Subscribers filter by
supplying an explicit list; empty list means "all events".
"""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


KNOWN_EVENTS: tuple[str, ...] = (
    "ticket.created",
    "ticket.assigned",
    "ticket.tagged",
    "ticket.priority_changed",
    "ticket.closed",
    "ticket.reopened",
    "ticket.sla_warned",
    "ticket.sla_breached",
    "rule.executed",
    "project_template.installed",
)


def _generate_secret() -> str:
    return "xtvwh_" + secrets.token_urlsafe(32)[:40]


def _hash_secret(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def build_router() -> APIRouter:
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel, Field

    from xtv_support.api.deps import get_db, require_scope
    from xtv_support.utils.time import utcnow

    router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

    class CreatePayload(BaseModel):
        url: str = Field(min_length=8, max_length=2048)
        events: list[str] = Field(default_factory=list)
        label: str | None = None

    @router.get("")
    async def list_webhooks(
        db=Depends(get_db),
        _key=Depends(require_scope("webhooks:write")),
    ) -> dict:
        cursor = (
            db.webhook_subscriptions.find(
                {},
                projection={"secret_hash": 0},
            )
            .sort("created_at", -1)
            .limit(200)
        )
        items: list[dict] = []
        async for doc in cursor:
            doc["_id"] = str(doc.get("_id"))
            items.append(doc)
        return {"items": items, "count": len(items)}

    @router.post("")
    async def create_webhook(
        body: CreatePayload,
        db=Depends(get_db),
        _key=Depends(require_scope("webhooks:write")),
    ) -> dict:
        bad = [e for e in body.events if e not in KNOWN_EVENTS]
        if bad:
            raise HTTPException(
                status_code=400,
                detail={"error": "unknown_events", "unknown": bad, "known": list(KNOWN_EVENTS)},
            )
        secret = _generate_secret()
        doc = {
            "url": body.url,
            "events": body.events,
            "label": body.label,
            "secret_hash": _hash_secret(secret),
            "created_at": utcnow(),
            "last_delivered_at": None,
            "revoked_at": None,
        }
        result = await db.webhook_subscriptions.insert_one(doc)
        return {
            "id": str(result.inserted_id),
            "secret": secret,  # shown exactly once
            "url": body.url,
            "events": body.events,
        }

    @router.delete("/{webhook_id}")
    async def revoke_webhook(
        webhook_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("webhooks:write")),
    ) -> dict:
        from bson import ObjectId

        try:
            oid = ObjectId(webhook_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"bad_id: {exc}") from exc
        result = await db.webhook_subscriptions.update_one(
            {"_id": oid, "revoked_at": None},
            {"$set": {"revoked_at": utcnow()}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="not_found")
        return {"ok": True, "revoked": webhook_id}

    return router
