"""``/api/v1/auth/accounts`` — admin account management (owner/admin only).

Minimal surface: list accounts with their resolved Role, and
soft-disable / re-enable an account. Disabling immediately revokes all
of that account's live sessions. No deletion — disable is reversible and
sufficient.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

_log = get_logger("api.accounts")


async def _require_manager(request: Request):
    """Gate: caller must resolve to Role ADMIN/OWNER (or hold admin:full)."""
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
    from fastapi import APIRouter, Depends, HTTPException

    from xtv_support.api.deps import get_db
    from xtv_support.api.routes.auth import _public_account
    from xtv_support.api.sessions import revoke_all_sessions_for
    from xtv_support.config.settings import settings
    from xtv_support.core.rbac import resolve_role
    from xtv_support.infrastructure.db import admin_accounts as accounts_repo

    router = APIRouter(prefix="/api/v1/auth/accounts", tags=["auth"])

    @router.get("", dependencies=[Depends(_require_manager)])
    async def list_accounts(db=Depends(get_db)) -> dict:
        accounts = await accounts_repo.list_all(db, include_disabled=True)
        items = []
        for acc in accounts:
            role = await resolve_role(db, acc.telegram_user_id, legacy_admin_ids=settings.ADMIN_IDS)
            items.append(_public_account(acc, role=str(role)))
        return {"items": items, "count": len(items)}

    @router.post("/{account_id}/disable", dependencies=[Depends(_require_manager)])
    async def disable_account(account_id: str, db=Depends(get_db)) -> dict:
        ok = await accounts_repo.set_disabled(db, account_id, disabled=True)
        if not ok:
            raise HTTPException(404, "account_not_found")
        await revoke_all_sessions_for(db, account_id)
        _log.info("auth.account_disabled", account_id=account_id)
        return {"ok": True}

    @router.post("/{account_id}/enable", dependencies=[Depends(_require_manager)])
    async def enable_account(account_id: str, db=Depends(get_db)) -> dict:
        ok = await accounts_repo.set_disabled(db, account_id, disabled=False)
        if not ok:
            raise HTTPException(404, "account_not_found")
        _log.info("auth.account_enabled", account_id=account_id)
        return {"ok": True}

    return router
