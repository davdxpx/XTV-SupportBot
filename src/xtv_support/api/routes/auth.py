"""``/api/v1/auth`` — admin web-console account auth.

Registration consumes (burns) a registration-capable API key as a
one-time invitation, deriving the new account's Telegram identity from
the key's ``target_user_id``. Login issues a server-side session cookie.
All authorization is read from the existing Role system elsewhere — this
module only handles authentication.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from fastapi import Request, Response

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

    from xtv_support.domain.models.admin_account import AdminAccount

_log = get_logger("api.auth")

USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
USERNAME_MIN = 3
USERNAME_MAX = 32
PASSWORD_MIN = 10
NAME_MAX = 64


def username_syntax_ok(username: str) -> bool:
    """3–32 chars, starts with a letter, alphanumeric + underscore only."""
    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        return False
    return bool(USERNAME_RE.match(username))


def _public_account(account: AdminAccount, *, role: str | None = None) -> dict[str, Any]:
    out = {
        "id": account.id,
        "username": account.username,
        "display_username": account.display_username,
        "first_name": account.first_name,
        "last_name": account.last_name,
        "telegram_user_id": account.telegram_user_id,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "last_login_at": account.last_login_at.isoformat() if account.last_login_at else None,
        "disabled_at": account.disabled_at.isoformat() if account.disabled_at else None,
    }
    if role is not None:
        out["role"] = role
    return out


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, raw_session: str) -> None:
    from xtv_support.config.settings import settings

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_session,
        max_age=settings.SESSION_TTL_DAYS * 86400,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException

    from xtv_support.api import ratelimit
    from xtv_support.api.deps import get_db
    from xtv_support.api.password import hash_password, verify_password
    from xtv_support.api.security import KEY_PREFIX, redeem_for_registration
    from xtv_support.api.sessions import create_session, revoke_session
    from xtv_support.config.settings import settings
    from xtv_support.infrastructure.db import admin_accounts as accounts_repo

    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

    @router.get("/check-username")
    async def check_username(username: str, db=Depends(get_db)) -> dict:
        if not username_syntax_ok(username):
            return {"available": False, "reason": "invalid_format"}
        if await accounts_repo.username_taken(db, username):
            return {"available": False, "reason": "taken"}
        return {"available": True, "reason": None}

    @router.post("/register", status_code=201)
    async def register(
        request: Request, response: Response, body: dict = Body(...), db=Depends(get_db)
    ) -> dict:
        api_key = str(body.get("api_key") or "").strip()
        username = str(body.get("username") or "").strip()
        first_name = str(body.get("first_name") or "").strip()
        last_name_raw = body.get("last_name")
        last_name = str(last_name_raw).strip() if last_name_raw else None
        password = str(body.get("password") or "")

        # 1. Key format sanity.
        if not api_key.startswith(KEY_PREFIX):
            raise HTTPException(400, "invalid_api_key_format")

        # 2. Atomically redeem + burn the invitation key.
        key = await redeem_for_registration(db, api_key)
        if key is None or key.target_user_id is None:
            # Vague to the client; real reason logged for the operator.
            _log.info("auth.register_rejected", reason="invalid_or_used_registration_key")
            raise HTTPException(403, "invalid_or_used_registration_key")

        # 3-6. Validate the rest. The key is already burned at this point;
        # that's acceptable — a malformed registration consumes the invite
        # and the operator simply issues a fresh one (errors here are the
        # invitee's own input, and we still want single-use semantics).
        if not username_syntax_ok(username):
            _log.info("auth.register_rejected", reason="invalid_username_format")
            raise HTTPException(400, "invalid_username_format")
        if await accounts_repo.username_taken(db, username):
            _log.info("auth.register_rejected", reason="username_taken")
            raise HTTPException(409, "username_taken")
        if not first_name or len(first_name) > NAME_MAX:
            _log.info("auth.register_rejected", reason="invalid_first_name")
            raise HTTPException(400, "invalid_first_name")
        if last_name is not None and len(last_name) > NAME_MAX:
            _log.info("auth.register_rejected", reason="invalid_first_name")
            raise HTTPException(400, "invalid_first_name")
        if len(password) < PASSWORD_MIN or password.lower() == username.lower():
            _log.info("auth.register_rejected", reason="weak_password")
            raise HTTPException(400, "weak_password")

        # 7. Only now hash + create.
        password_hash = hash_password(password)
        try:
            account = await accounts_repo.create(
                db,
                username=username,
                display_username=username,
                first_name=first_name,
                last_name=last_name,
                password_hash=password_hash,
                telegram_user_id=key.target_user_id,
                created_via_key_id=key.key_id,
            )
        except accounts_repo.UsernameTaken as exc:
            _log.info("auth.register_rejected", reason="username_taken_race")
            raise HTTPException(409, "username_taken") from exc

        # 8. Log them in immediately.
        raw_session = await create_session(db, account.id, ttl_days=settings.SESSION_TTL_DAYS)
        _set_session_cookie(response, raw_session)
        await accounts_repo.touch_last_login(db, account.id)
        _log.info(
            "auth.account_registered",
            username=account.username,
            telegram_user_id=account.telegram_user_id,
            created_via_key_id=account.created_via_key_id,
        )
        return {"account": _public_account(account)}

    @router.post("/login")
    async def login(
        request: Request, response: Response, body: dict = Body(...), db=Depends(get_db)
    ) -> dict:
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "")

        rl_key = f"{_client_ip(request)}|{username.lower()}"
        if not ratelimit.check_and_record(rl_key):
            raise HTTPException(429, "too_many_attempts")

        # Identical generic error for unknown / wrong-password / disabled —
        # no account-enumeration or "exists but disabled" disclosure.
        account = await accounts_repo.get_by_username(db, username)
        ok = (
            account is not None
            and account.disabled_at is None
            and verify_password(account.password_hash, password)
        )
        if not ok or account is None:
            _log.info("auth.login_failed", username=username.lower())
            raise HTTPException(401, "invalid_credentials")

        raw_session = await create_session(db, account.id, ttl_days=settings.SESSION_TTL_DAYS)
        _set_session_cookie(response, raw_session)
        await accounts_repo.touch_last_login(db, account.id)
        _log.info("auth.login_ok", username=account.username, account_id=account.id)
        return {"account": _public_account(account)}

    @router.post("/logout")
    async def logout(request: Request, response: Response, db=Depends(get_db)) -> dict:
        raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if raw:
            await revoke_session(db, raw)
        response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
        return {"ok": True}

    return router
