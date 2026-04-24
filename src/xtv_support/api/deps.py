"""FastAPI dependencies for the REST API.

Thin wrappers that resolve the DB + ApiKey from request state. Kept
in a separate module so route files don't reach into server internals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import Request
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from xtv_support.api.security import ApiKey


def _fastapi():
    """Lazy import so the module loads without fastapi installed."""
    import fastapi

    return fastapi


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
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise _fastapi().HTTPException(status_code=503, detail="database_unavailable")
    key = await lookup_by_key(db, token)
    if key is None:
        raise _fastapi().HTTPException(status_code=401, detail="invalid_key")
    return key


def require_scope(scope: str):
    """Return a dependency that enforces ``scope`` on ``current_api_key``."""

    async def _dep(request: Request):
        from xtv_support.api.security import scope_satisfies

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
        return key

    return _dep
