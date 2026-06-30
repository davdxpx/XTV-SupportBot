"""Server-side admin sessions.

DB-backed (collection ``sessions``) rather than stateless JWTs so a
session can be revoked instantly — disabling an account must kill its
live sessions on their very next request. The raw session id lives only
in the httpOnly cookie; the DB stores a SHA-256 hash of it (mirroring
``api.security.hash_key``), so a DB read leak hands out no live tokens.

A native Mongo TTL index on ``expires_at`` reaps expired docs; we also
re-check ``expires_at`` and the linked account's ``disabled_at`` on every
resolve so neither stale clocks nor a just-disabled account slip through.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, timedelta
from typing import TYPE_CHECKING

from xtv_support.infrastructure.db import admin_accounts as accounts_repo
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from xtv_support.domain.models.admin_account import AdminAccount


def _hash(raw_session_id: str) -> str:
    return hashlib.sha256(raw_session_id.encode()).hexdigest()


async def create_session(db: AsyncIOMotorDatabase, account_id: str, *, ttl_days: int = 30) -> str:
    """Create a session for ``account_id`` and return the raw id (for the cookie)."""
    raw = secrets.token_urlsafe(32)
    now = utcnow()
    await db.sessions.insert_one(
        {
            "session_hash": _hash(raw),
            "account_id": account_id,
            "created_at": now,
            "expires_at": now + timedelta(days=ttl_days),
            "last_seen_at": now,
        }
    )
    return raw


async def resolve_session(db: AsyncIOMotorDatabase, raw_session_id: str) -> AdminAccount | None:
    """Return the live :class:`AdminAccount` behind a cookie, or ``None``."""
    if not raw_session_id:
        return None
    doc = await db.sessions.find_one({"session_hash": _hash(raw_session_id)})
    if doc is None:
        return None
    expires_at = doc.get("expires_at")
    if expires_at is None:
        return None
    # Motor runs with tz_aware=True in prod, but a naive value (e.g. from
    # a test mock) must be treated as UTC to stay comparable.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= utcnow():
        return None
    account = await accounts_repo.get_by_id(db, str(doc.get("account_id")))
    if account is None or account.disabled_at is not None:
        return None
    await db.sessions.update_one({"_id": doc["_id"]}, {"$set": {"last_seen_at": utcnow()}})
    return account


async def revoke_session(db: AsyncIOMotorDatabase, raw_session_id: str) -> None:
    if not raw_session_id:
        return
    await db.sessions.delete_one({"session_hash": _hash(raw_session_id)})


async def revoke_all_sessions_for(db: AsyncIOMotorDatabase, account_id: str) -> None:
    await db.sessions.delete_many({"account_id": account_id})


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
