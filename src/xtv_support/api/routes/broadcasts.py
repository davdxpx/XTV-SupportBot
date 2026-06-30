"""``/api/v1/broadcasts`` — compose & monitor broadcasts (owner/admin only).

Brings the bot's broadcast surface to the admin console. Sending is a
high-consequence action (messages every active user), so the create route
delegates to the existing :class:`BroadcastManager` (one broadcast at a
time, persistent, FloodWait-aware) and the UI guards it behind a typed
confirmation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

_log = get_logger("api.broadcasts")


async def _require_manager_role(request: Request) -> None:
    from fastapi import HTTPException

    from xtv_support.api.deps import current_principal, get_db
    from xtv_support.api.security import ApiKey, scope_satisfies
    from xtv_support.config.settings import settings
    from xtv_support.core.rbac import resolve_role
    from xtv_support.domain.enums import Role
    from xtv_support.domain.models.admin_account import AdminAccount

    principal = await current_principal(request)
    db = await get_db(request)
    if isinstance(principal, AdminAccount):
        role = await resolve_role(
            db, principal.telegram_user_id, legacy_admin_ids=settings.ADMIN_IDS
        )
        if not role.can(Role.ADMIN):
            raise HTTPException(403, "insufficient_role")
        return
    if isinstance(principal, ApiKey) and scope_satisfies(principal.scopes, "admin:full"):
        return
    raise HTTPException(403, "insufficient_role")


def _resolve_broadcast_manager(request: Request):
    """Resolve the BroadcastManager from the container, or None (degrade)."""
    container = getattr(request.app.state, "container", None)
    if container is None:
        return None
    try:
        from xtv_support.services.broadcasts.service import BroadcastManager

        return container.resolve(BroadcastManager)
    except Exception as exc:  # noqa: BLE001
        _log.debug("api.broadcasts.manager_unavailable", error=str(exc))
        return None


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException

    from xtv_support.api.deps import get_db
    from xtv_support.infrastructure.db import broadcasts as broadcasts_repo

    router = APIRouter(prefix="/api/v1/broadcasts", tags=["broadcasts"])

    def _row(d: dict) -> dict:
        return {
            "id": str(d.get("_id")),
            "text": (d.get("text") or "")[:200],
            "state": d.get("state"),
            "total": d.get("total", 0),
            "sent": d.get("sent", 0),
            "failed": d.get("failed", 0),
            "blocked": d.get("blocked_count", 0),
            "started_at": d.get("started_at").isoformat() if d.get("started_at") else None,
            "finished_at": d.get("finished_at").isoformat() if d.get("finished_at") else None,
        }

    @router.get("")
    async def list_broadcasts(db=Depends(get_db), _=Depends(_require_manager_role)) -> dict:
        items = [_row(d) for d in await broadcasts_repo.list_recent(db, limit=50)]
        active = await broadcasts_repo.find_active(db) is not None
        return {"items": items, "count": len(items), "active": active}

    @router.post("", status_code=201)
    async def create_broadcast(
        request: Request, body: dict = Body(...), _=Depends(_require_manager_role)
    ) -> dict:
        text = (body.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "empty_text")
        if len(text) > 4096:
            raise HTTPException(400, "text_too_long")
        manager = _resolve_broadcast_manager(request)
        if manager is None:
            raise HTTPException(503, "broadcasts_unavailable")
        bid = await manager.start_from_web(text=text)
        if bid is None:
            raise HTTPException(409, "broadcast_already_running")
        _log.info("api.broadcasts.started", broadcast_id=str(bid))
        return {"ok": True, "id": str(bid)}

    @router.post("/cancel")
    async def cancel_broadcast(request: Request, _=Depends(_require_manager_role)) -> dict:
        manager = _resolve_broadcast_manager(request)
        if manager is None:
            raise HTTPException(503, "broadcasts_unavailable")
        await manager.cancel()
        _log.info("api.broadcasts.cancel_requested")
        return {"ok": True}

    return router
