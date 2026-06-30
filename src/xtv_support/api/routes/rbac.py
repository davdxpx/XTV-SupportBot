"""``/api/v1/rbac`` — web management for Roles & Teams (owner/admin only).

Brings the bot's ``/role`` and ``/team`` surfaces to the admin console,
reusing the existing :mod:`infrastructure.db.roles` and
:mod:`infrastructure.db.teams` repositories. Authorization is the same
Role hierarchy used everywhere else; a caller can never grant a role
above their own rank.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

    from xtv_support.domain.enums import Role

_log = get_logger("api.rbac")


async def _require_manager(request: Request) -> Role:
    """Resolve the caller and require ADMIN/OWNER. Returns the caller's Role.

    Session accounts resolve their real Role; a legacy ``admin:full`` API
    key is treated as OWNER (it already grants everything).
    """
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
        return role
    if isinstance(principal, ApiKey) and scope_satisfies(principal.scopes, "admin:full"):
        return Role.OWNER
    raise HTTPException(403, "insufficient_role")


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException

    from xtv_support.api.deps import get_db
    from xtv_support.domain.enums import Role
    from xtv_support.infrastructure.db import roles as roles_repo
    from xtv_support.infrastructure.db import teams as teams_repo

    router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])

    def _role_dict(a) -> dict:
        return {
            "user_id": a.user_id,
            "role": str(a.role),
            "team_ids": list(a.team_ids),
            "granted_by": a.granted_by,
            "granted_at": a.granted_at.isoformat() if a.granted_at else None,
        }

    def _team_dict(t) -> dict:
        return {
            "id": t.id,
            "name": t.name,
            "timezone": t.timezone,
            "member_ids": list(t.member_ids),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

    # ---- Roles -------------------------------------------------------------
    @router.get("/roles")
    async def list_roles(db=Depends(get_db), _=Depends(_require_manager)) -> dict:
        items = [_role_dict(a) for a in await roles_repo.list_all(db)]
        return {"items": items, "count": len(items), "roles": [str(r) for r in Role]}

    @router.post("/roles")
    async def grant_role(request: Request, body: dict = Body(...), db=Depends(get_db)) -> dict:
        caller_role = await _require_manager(request)
        try:
            user_id = int(body.get("user_id"))
        except (TypeError, ValueError):
            raise HTTPException(400, "invalid_user_id") from None
        try:
            role = Role(str(body.get("role") or "").strip().lower())
        except ValueError:
            raise HTTPException(400, "invalid_role") from None
        # A caller can never grant a role above their own rank.
        if role.rank > caller_role.rank:
            raise HTTPException(403, "cannot_grant_above_self")
        team_ids = body.get("team_ids")
        await roles_repo.grant(
            db,
            user_id=user_id,
            role=role,
            granted_by=None,
            team_ids=list(team_ids) if isinstance(team_ids, list) else None,
        )
        _log.info("api.rbac.role_granted", user_id=user_id, role=str(role))
        return {"ok": True, "user_id": user_id, "role": str(role)}

    @router.delete("/roles/{user_id}")
    async def revoke_role(request: Request, user_id: int, db=Depends(get_db)) -> dict:
        caller_role = await _require_manager(request)
        existing = await roles_repo.get_role(db, user_id)
        # Can't strip someone ranked above you.
        if existing is not None and existing.role.rank > caller_role.rank:
            raise HTTPException(403, "cannot_revoke_above_self")
        await roles_repo.revoke(db, user_id)
        _log.info("api.rbac.role_revoked", user_id=user_id)
        return {"ok": True, "user_id": user_id}

    # ---- Teams -------------------------------------------------------------
    @router.get("/teams")
    async def list_teams(db=Depends(get_db), _=Depends(_require_manager)) -> dict:
        items = [_team_dict(t) for t in await teams_repo.list_all(db)]
        return {"items": items, "count": len(items)}

    @router.post("/teams")
    async def create_team(
        body: dict = Body(...), db=Depends(get_db), _=Depends(_require_manager)
    ) -> dict:
        team_id = (body.get("team_id") or "").strip().lower()
        name = (body.get("name") or "").strip()
        if not name:
            raise HTTPException(400, "missing_name")
        if await teams_repo.get(db, team_id) is not None:
            raise HTTPException(409, "team_exists")
        try:
            team = await teams_repo.create(
                db,
                team_id=team_id,
                name=name,
                timezone=(body.get("timezone") or "UTC"),
                created_by=0,
            )
        except teams_repo.InvalidSlugError as exc:
            raise HTTPException(400, "invalid_team_id") from exc
        _log.info("api.rbac.team_created", team_id=team.id)
        return {"ok": True, "team": _team_dict(team)}

    @router.delete("/teams/{team_id}")
    async def delete_team(team_id: str, db=Depends(get_db), _=Depends(_require_manager)) -> dict:
        ok = await teams_repo.delete(db, team_id)
        if not ok:
            raise HTTPException(404, "team_not_found")
        _log.info("api.rbac.team_deleted", team_id=team_id)
        return {"ok": True}

    @router.post("/teams/{team_id}/members")
    async def add_member(
        team_id: str, body: dict = Body(...), db=Depends(get_db), _=Depends(_require_manager)
    ) -> dict:
        if await teams_repo.get(db, team_id) is None:
            raise HTTPException(404, "team_not_found")
        try:
            user_id = int(body.get("user_id"))
        except (TypeError, ValueError):
            raise HTTPException(400, "invalid_user_id") from None
        await teams_repo.add_member(db, team_id, user_id)
        return {"ok": True}

    @router.delete("/teams/{team_id}/members/{user_id}")
    async def remove_member(
        team_id: str, user_id: int, db=Depends(get_db), _=Depends(_require_manager)
    ) -> dict:
        await teams_repo.remove_member(db, team_id, user_id)
        return {"ok": True}

    return router
