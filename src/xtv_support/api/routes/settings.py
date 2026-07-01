"""``/api/v1/settings`` — live, admin-editable operational settings (owner/admin).

Only the allowlisted operational knobs in :mod:`xtv_support.config.runtime` are
exposed; secrets and infra settings stay env-only and can never be set here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

_log = get_logger("api.settings")


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


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException

    from xtv_support.api.deps import get_db
    from xtv_support.config import runtime
    from xtv_support.infrastructure.db import app_settings as store

    router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

    @router.get("")
    async def get_settings(db=Depends(get_db), _=Depends(_require_manager_role)) -> dict:
        overrides = await store.get_overrides(db)
        return {"items": runtime.describe(overrides)}

    @router.patch("")
    async def patch_settings(
        body: dict = Body(...), db=Depends(get_db), _=Depends(_require_manager_role)
    ) -> dict:
        if not isinstance(body, dict) or not body:
            raise HTTPException(400, "empty_body")
        validated: dict = {}
        for key, raw in body.items():
            spec = runtime.SPEC_BY_KEY.get(key)
            if spec is None:
                raise HTTPException(400, f"unknown_setting:{key}")
            try:
                validated[key] = runtime.coerce(spec, raw)
            except (ValueError, TypeError) as exc:
                raise HTTPException(400, f"invalid_value:{key}") from exc
        await store.set_overrides(db, validated)
        runtime.invalidate()
        _log.info("api.settings.updated", keys=list(validated.keys()))
        overrides = await store.get_overrides(db)
        return {"ok": True, "items": runtime.describe(overrides)}

    return router
