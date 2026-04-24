"""API-key authentication helpers.

Keys live in the ``api_keys`` Mongo collection, hashed with SHA-256 so
a DB leak doesn't expose live secrets. At creation time we return the
plaintext once; everything after goes through :func:`lookup_by_key`.

Scope model
-----------
A key carries a list of scope strings. Routes declare the scope they
need via :func:`require_scope`; the dependency resolves the current
key from the ``Authorization: Bearer <key>`` header and raises HTTP
401 / 403 accordingly.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

_log = get_logger("api.security")

KEY_PREFIX = "xtv_"
KEY_LENGTH = 40  # 40 random chars after the prefix


# Known scopes — kept centralised so typos become loud.
SCOPES: tuple[str, ...] = (
    "tickets:read",
    "tickets:write",
    "projects:read",
    "projects:write",
    "users:read",
    "analytics:read",
    "webhooks:write",
    "rules:read",
    "admin:full",
)


@dataclass(frozen=True, slots=True)
class ApiKey:
    key_id: str
    label: str
    scopes: tuple[str, ...]
    created_by: int | None
    created_at: datetime | None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewApiKey:
    """Returned once at creation — plaintext key + metadata."""

    plaintext: str
    meta: ApiKey


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def generate_key() -> str:
    """Return a new plaintext key (format ``xtv_<40 random>``)."""
    return KEY_PREFIX + secrets.token_urlsafe(32)[:KEY_LENGTH]


def scope_satisfies(key_scopes: tuple[str, ...], required: str) -> bool:
    """``admin:full`` grants everything; otherwise equality."""
    if "admin:full" in key_scopes:
        return True
    return required in key_scopes


# ----------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------
async def create_key(
    db: AsyncIOMotorDatabase,
    *,
    label: str,
    scopes: list[str],
    created_by: int,
) -> NewApiKey:
    bad = [s for s in scopes if s not in SCOPES]
    if bad:
        raise ValueError(f"Unknown scope(s): {', '.join(bad)}")
    plaintext = generate_key()
    doc = {
        "hash": hash_key(plaintext),
        "label": label,
        "scopes": list(scopes),
        "created_by": created_by,
        "created_at": utcnow(),
        "revoked_at": None,
        "last_used_at": None,
    }
    result = await db.api_keys.insert_one(doc)
    meta = ApiKey(
        key_id=str(result.inserted_id),
        label=label,
        scopes=tuple(scopes),
        created_by=created_by,
        created_at=doc["created_at"],
    )
    _log.info("api_key.created", label=label, scopes=scopes, by=created_by)
    return NewApiKey(plaintext=plaintext, meta=meta)


async def lookup_by_key(db: AsyncIOMotorDatabase, plaintext: str) -> ApiKey | None:
    """Return the :class:`ApiKey` matching ``plaintext`` or ``None``."""
    if not plaintext or not plaintext.startswith(KEY_PREFIX):
        return None
    doc = await db.api_keys.find_one({"hash": hash_key(plaintext), "revoked_at": None})
    if doc is None:
        return None
    # Best-effort: bump last_used_at without blocking.
    try:
        await db.api_keys.update_one({"_id": doc["_id"]}, {"$set": {"last_used_at": utcnow()}})
    except Exception as exc:  # noqa: BLE001
        _log.debug("api_key.touch_failed", error=str(exc))
    return ApiKey(
        key_id=str(doc.get("_id")),
        label=str(doc.get("label") or ""),
        scopes=tuple(doc.get("scopes") or ()),
        created_by=doc.get("created_by"),
        created_at=doc.get("created_at"),
        last_used_at=doc.get("last_used_at"),
        revoked_at=doc.get("revoked_at"),
    )


async def revoke_key(db: AsyncIOMotorDatabase, key_id: str) -> bool:
    from bson import ObjectId

    result = await db.api_keys.update_one(
        {"_id": ObjectId(key_id), "revoked_at": None},
        {"$set": {"revoked_at": utcnow()}},
    )
    return result.matched_count == 1


async def list_keys(db: AsyncIOMotorDatabase, *, include_revoked: bool = False) -> list[ApiKey]:
    query: dict = {} if include_revoked else {"revoked_at": None}
    cursor = db.api_keys.find(query).sort("created_at", -1)
    out: list[ApiKey] = []
    async for doc in cursor:
        out.append(
            ApiKey(
                key_id=str(doc.get("_id")),
                label=str(doc.get("label") or ""),
                scopes=tuple(doc.get("scopes") or ()),
                created_by=doc.get("created_by"),
                created_at=doc.get("created_at"),
                last_used_at=doc.get("last_used_at"),
                revoked_at=doc.get("revoked_at"),
            )
        )
    return out
