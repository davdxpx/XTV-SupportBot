"""``/api/v1/apikeys`` — web management for API keys (owner/admin only).

Brings the bot's ``/apikey`` surface to the admin console: list, mint
(bearer keys or single-use registration invites), and revoke. Reuses
:mod:`xtv_support.api.security`. The plaintext key is returned exactly
once, at creation — everything after is metadata only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

_log = get_logger("api.apikeys")


async def _require_manager(request: Request) -> int:
    """Require ADMIN/OWNER. Returns the caller's Telegram id (for created_by)."""
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
        return principal.telegram_user_id
    if isinstance(principal, ApiKey) and scope_satisfies(principal.scopes, "admin:full"):
        return principal.created_by or 0
    raise HTTPException(403, "insufficient_role")


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException, Query

    from xtv_support.api import security as api_sec
    from xtv_support.api.deps import get_db

    router = APIRouter(prefix="/api/v1/apikeys", tags=["apikeys"])

    def _key_dict(k: api_sec.ApiKey) -> dict:
        return {
            "key_id": k.key_id,
            "label": k.label,
            "scopes": list(k.scopes),
            "created_by": k.created_by,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            "registration_capable": k.registration_capable,
            "registration_used_at": (
                k.registration_used_at.isoformat() if k.registration_used_at else None
            ),
            "target_user_id": k.target_user_id,
        }

    @router.get("")
    async def list_keys(
        db=Depends(get_db),
        _caller: int = Depends(_require_manager),
        include_revoked: bool = Query(False),
    ) -> dict:
        keys = await api_sec.list_keys(db, include_revoked=include_revoked)
        return {
            "items": [_key_dict(k) for k in keys],
            "count": len(keys),
            "scopes": list(api_sec.SCOPES),
        }

    @router.post("", status_code=201)
    async def create_key(request: Request, body: dict = Body(...), db=Depends(get_db)) -> dict:
        caller_id = await _require_manager(request)
        label = (body.get("label") or "").strip() or "web"
        scopes = body.get("scopes") or []
        if not isinstance(scopes, list):
            raise HTTPException(400, "invalid_scopes")
        allow_registration = bool(body.get("allow_registration"))
        target_user_id = body.get("target_user_id")
        if allow_registration:
            try:
                target_user_id = int(target_user_id)
            except (TypeError, ValueError):
                raise HTTPException(400, "invite_requires_target_user_id") from None
            scopes = []  # invites carry no bearer power; they're burned on redeem
        try:
            created = await api_sec.create_key(
                db,
                label=label,
                scopes=scopes,
                created_by=caller_id,
                allow_registration=allow_registration,
                target_user_id=target_user_id if allow_registration else None,
            )
        except ValueError as exc:  # unknown scope / missing target
            raise HTTPException(400, str(exc)) from exc
        _log.info(
            "api.apikeys.created",
            label=label,
            by=caller_id,
            registration_capable=allow_registration,
        )
        # Plaintext returned exactly once.
        return {"plaintext": created.plaintext, "key": _key_dict(created.meta)}

    @router.delete("/{key_id}")
    async def revoke_key(
        key_id: str, db=Depends(get_db), _caller: int = Depends(_require_manager)
    ) -> dict:
        ok = await api_sec.revoke_key(db, key_id)
        if not ok:
            raise HTTPException(404, "key_not_found")
        _log.info("api.apikeys.revoked", key_id=key_id)
        return {"ok": True}

    return router
