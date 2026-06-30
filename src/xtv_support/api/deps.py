"""FastAPI dependencies for the REST API.

Three authentication mechanisms coexist:

1. Telegram Mini-App ``initData`` header  → :class:`TelegramUser`
2. Admin web-console session cookie       → :class:`AdminAccount`
3. Legacy ``Authorization: Bearer`` key   → :class:`ApiKey`

:func:`current_principal` resolves the raw identity in that precedence
order (used by ``/me`` and the account-management routes, which then
resolve a real Role themselves). :func:`require_scope` is the gate for
the admin-data routes: it accepts a session cookie (mapped to the
existing Role hierarchy) **or** a legacy bearer key (scope-checked),
and returns a uniform :class:`Principal` carrying the actor's Telegram
id as ``created_by`` so existing routes keep attributing writes
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Request

from xtv_support.domain.enums import Role

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from xtv_support.api.security import ApiKey
    from xtv_support.domain.models.admin_account import AdminAccount


def _fastapi():
    """Lazy import so the module loads without fastapi installed."""
    import fastapi

    return fastapi


# Minimum Role required for each API scope when the caller authenticates
# as an AdminAccount. Legacy bearer keys are still checked by their
# explicit scope list via ``scope_satisfies``; this map only governs the
# session-cookie path. Unknown scopes fail safe (require ADMIN).
_SCOPE_MIN_ROLE: dict[str, Role] = {
    "tickets:read": Role.VIEWER,
    "projects:read": Role.VIEWER,
    "users:read": Role.AGENT,
    "analytics:read": Role.AGENT,
    "rules:read": Role.AGENT,
    "tickets:write": Role.AGENT,
    "projects:write": Role.SUPERVISOR,
    "rules:write": Role.SUPERVISOR,
    "webhooks:write": Role.ADMIN,
    "admin:full": Role.ADMIN,
}


@dataclass(frozen=True, slots=True)
class Principal:
    """Uniform authenticated actor for the admin-data routes."""

    kind: str  # "account" | "apikey"
    actor_id: int | None
    role: Role | None = None
    account: AdminAccount | None = None
    api_key: ApiKey | None = None

    @property
    def created_by(self) -> int | None:
        """Telegram id of the acting human — for write attribution."""
        return self.actor_id


async def get_db(request: Request) -> AsyncIOMotorDatabase:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise _fastapi().HTTPException(status_code=503, detail="database_unavailable")
    return db


async def current_api_key(request: Request) -> ApiKey:
    """Resolve the bearer key from ``Authorization: Bearer <key>``."""
    from xtv_support.api.security import lookup_by_key

    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise _fastapi().HTTPException(status_code=401, detail="missing_bearer")
    token = auth.split(None, 1)[1].strip()
    db = await get_db(request)
    key = await lookup_by_key(db, token)
    if key is None:
        raise _fastapi().HTTPException(status_code=401, detail="invalid_key")
    return key


async def current_admin_account(request: Request) -> AdminAccount:
    """Resolve the AdminAccount behind the session cookie, or 401."""
    from xtv_support.api.sessions import resolve_session
    from xtv_support.config.settings import settings

    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not raw:
        raise _fastapi().HTTPException(status_code=401, detail="missing_session")
    db = await get_db(request)
    account = await resolve_session(db, raw)
    if account is None:
        raise _fastapi().HTTPException(status_code=401, detail="invalid_session")
    return account


async def current_principal(request: Request):
    """Resolve the raw identity, precedence: initData → session → bearer.

    Returns a :class:`TelegramUser`, :class:`AdminAccount`, or
    :class:`ApiKey`. Raises 401 if no mechanism authenticates. Callers
    that need authorization resolve a Role from the returned identity
    themselves (see ``/me`` and the account routes).
    """
    from xtv_support.api.auth_webapp import INIT_DATA_HEADER, current_tg_user
    from xtv_support.config.settings import settings

    if request.headers.get(INIT_DATA_HEADER):
        return await current_tg_user(request)
    if request.cookies.get(settings.SESSION_COOKIE_NAME):
        return await current_admin_account(request)
    return await current_api_key(request)


def require_scope(scope: str):
    """Gate an admin-data route on ``scope``.

    Session-cookie callers (AdminAccount) are checked against the
    existing Role hierarchy via ``_SCOPE_MIN_ROLE``; legacy bearer keys
    are checked against their explicit scopes. Returns a
    :class:`Principal`.
    """

    async def _dep(request: Request) -> Principal:
        from xtv_support.api.security import scope_satisfies
        from xtv_support.config.settings import settings
        from xtv_support.core.rbac import resolve_role

        db = await get_db(request)

        if request.cookies.get(settings.SESSION_COOKIE_NAME):
            account = await current_admin_account(request)
            role = await resolve_role(
                db, account.telegram_user_id, legacy_admin_ids=settings.ADMIN_IDS
            )
            required_role = _SCOPE_MIN_ROLE.get(scope, Role.ADMIN)
            if not role.can(required_role):
                raise _fastapi().HTTPException(
                    status_code=403,
                    detail={
                        "error": "insufficient_role",
                        "required": str(required_role),
                        "granted": str(role),
                    },
                )
            return Principal(
                kind="account", actor_id=account.telegram_user_id, role=role, account=account
            )

        key = await current_api_key(request)
        if not scope_satisfies(key.scopes, scope):
            raise _fastapi().HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_scope",
                    "required": scope,
                    "granted": list(key.scopes),
                },
            )
        return Principal(kind="apikey", actor_id=key.created_by, api_key=key)

    return _dep


async def current_tg_user_or_apikey(request: Request):
    """Unified auth — WebApp ``initData`` takes precedence over API keys.

    Kept for backward compatibility. New code should prefer
    :func:`current_principal` (which also understands session cookies).
    """
    from xtv_support.api.auth_webapp import INIT_DATA_HEADER, current_tg_user

    if request.headers.get(INIT_DATA_HEADER):
        return await current_tg_user(request)
    return await current_api_key(request)
