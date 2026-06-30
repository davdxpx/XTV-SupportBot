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
    "rules:write",
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
    # Registration invites: a key minted with ``allow_registration=True``
    # may be redeemed exactly once to create an AdminAccount, after which
    # it is burned (revoked) for both registration and bearer-token use.
    # ``target_user_id`` is the Telegram identity the new account binds to
    # — the invitee, NOT ``created_by`` (the admin who issued the invite).
    registration_capable: bool = False
    registration_used_at: datetime | None = None
    target_user_id: int | None = None


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
    allow_registration: bool = False,
    target_user_id: int | None = None,
) -> NewApiKey:
    bad = [s for s in scopes if s not in SCOPES]
    if bad:
        raise ValueError(f"Unknown scope(s): {', '.join(bad)}")
    if allow_registration and target_user_id is None:
        raise ValueError("registration-capable keys require a target_user_id")
    plaintext = generate_key()
    doc = {
        "hash": hash_key(plaintext),
        "label": label,
        "scopes": list(scopes),
        "created_by": created_by,
        "created_at": utcnow(),
        "revoked_at": None,
        "last_used_at": None,
        "registration_capable": allow_registration,
        "registration_used_at": None,
        "target_user_id": target_user_id if allow_registration else None,
    }
    result = await db.api_keys.insert_one(doc)
    meta = ApiKey(
        key_id=str(result.inserted_id),
        label=label,
        scopes=tuple(scopes),
        created_by=created_by,
        created_at=doc["created_at"],
        registration_capable=allow_registration,
        target_user_id=doc["target_user_id"],
    )
    _log.info(
        "api_key.created",
        label=label,
        scopes=scopes,
        by=created_by,
        registration_capable=allow_registration,
        target_user_id=doc["target_user_id"],
    )
    return NewApiKey(plaintext=plaintext, meta=meta)


async def redeem_for_registration(db: AsyncIOMotorDatabase, plaintext: str) -> ApiKey | None:
    """Atomically claim a registration-capable key and burn it.

    A single ``find_one_and_update`` matches only an unused,
    non-revoked, registration-capable key and, in the same operation,
    sets both ``registration_used_at`` and ``revoked_at`` — so the key
    dies for registration AND for bearer-token auth at once, and two
    concurrent redemptions can never both win. Returns the redeemed
    :class:`ApiKey` (with its ``target_user_id``) or ``None``.
    """
    if not plaintext or not plaintext.startswith(KEY_PREFIX):
        return None
    now = utcnow()
    doc = await db.api_keys.find_one_and_update(
        {
            "hash": hash_key(plaintext),
            "registration_capable": True,
            "registration_used_at": None,
            "revoked_at": None,
        },
        {"$set": {"registration_used_at": now, "revoked_at": now}},
    )
    if doc is None:
        return None
    return ApiKey(
        key_id=str(doc.get("_id")),
        label=str(doc.get("label") or ""),
        scopes=tuple(doc.get("scopes") or ()),
        created_by=doc.get("created_by"),
        created_at=doc.get("created_at"),
        last_used_at=doc.get("last_used_at"),
        revoked_at=now,
        registration_capable=True,
        registration_used_at=now,
        target_user_id=doc.get("target_user_id"),
    )


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
        registration_capable=bool(doc.get("registration_capable")),
        registration_used_at=doc.get("registration_used_at"),
        target_user_id=doc.get("target_user_id"),
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
                registration_capable=bool(doc.get("registration_capable")),
                registration_used_at=doc.get("registration_used_at"),
                target_user_id=doc.get("target_user_id"),
            )
        )
    return out
