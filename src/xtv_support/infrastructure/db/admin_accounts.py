"""Admin-account repository.

Stores one document per web-console account in ``admin_accounts``::

    {_id, username, display_username, first_name, last_name,
     password_hash, telegram_user_id, created_at, created_via_key_id,
     last_login_at, disabled_at}

``username`` is stored **lowercase** and carries a unique index, so the
unique constraint is the single source of truth for "is this name taken".
Application-level checks are best-effort; :func:`create` still catches the
``DuplicateKeyError`` from the inevitable check-then-insert TOCTOU race.
"""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from xtv_support.domain.models.admin_account import AdminAccount
from xtv_support.utils.ids import safe_objectid
from xtv_support.utils.time import utcnow


class UsernameTaken(Exception):
    """Raised by :func:`create` when the username unique index rejects the insert."""


async def create(
    db: AsyncIOMotorDatabase,
    *,
    username: str,
    display_username: str,
    first_name: str,
    last_name: str | None,
    password_hash: str,
    telegram_user_id: int,
    created_via_key_id: str,
) -> AdminAccount:
    doc = {
        "username": username.lower(),
        "display_username": display_username,
        "first_name": first_name,
        "last_name": last_name,
        "password_hash": password_hash,
        "telegram_user_id": telegram_user_id,
        "created_at": utcnow(),
        "created_via_key_id": created_via_key_id,
        "last_login_at": None,
        "disabled_at": None,
    }
    try:
        result = await db.admin_accounts.insert_one(doc)
    except DuplicateKeyError as exc:
        raise UsernameTaken(username) from exc
    return _account_from_doc({**doc, "_id": result.inserted_id})


async def get_by_username(db: AsyncIOMotorDatabase, username: str) -> AdminAccount | None:
    doc = await db.admin_accounts.find_one({"username": username.lower()})
    return _account_from_doc(doc) if doc else None


async def get_by_id(db: AsyncIOMotorDatabase, account_id: str) -> AdminAccount | None:
    oid = safe_objectid(account_id)
    if oid is None:
        return None
    doc = await db.admin_accounts.find_one({"_id": oid})
    return _account_from_doc(doc) if doc else None


async def list_all(
    db: AsyncIOMotorDatabase, *, include_disabled: bool = False
) -> list[AdminAccount]:
    query: dict[str, Any] = {} if include_disabled else {"disabled_at": None}
    cursor = db.admin_accounts.find(query).sort("created_at", -1)
    return [_account_from_doc(doc) async for doc in cursor]


async def set_disabled(db: AsyncIOMotorDatabase, account_id: str, *, disabled: bool) -> bool:
    oid = safe_objectid(account_id)
    if oid is None:
        return False
    result = await db.admin_accounts.update_one(
        {"_id": oid}, {"$set": {"disabled_at": utcnow() if disabled else None}}
    )
    return result.matched_count == 1


async def touch_last_login(db: AsyncIOMotorDatabase, account_id: str) -> None:
    oid = safe_objectid(account_id)
    if oid is None:
        return
    await db.admin_accounts.update_one({"_id": oid}, {"$set": {"last_login_at": utcnow()}})


async def username_taken(db: AsyncIOMotorDatabase, username: str) -> bool:
    """Indexed existence check against the lowercase ``username``."""
    doc = await db.admin_accounts.find_one({"username": username.lower()}, {"_id": 1})
    return doc is not None


def _account_from_doc(doc: dict[str, Any]) -> AdminAccount:
    return AdminAccount(
        id=str(doc["_id"]),
        username=str(doc["username"]),
        display_username=str(doc.get("display_username") or doc["username"]),
        first_name=str(doc.get("first_name") or ""),
        last_name=doc.get("last_name"),
        password_hash=str(doc.get("password_hash") or ""),
        telegram_user_id=int(doc["telegram_user_id"]),
        created_at=doc.get("created_at"),
        created_via_key_id=str(doc.get("created_via_key_id") or ""),
        last_login_at=doc.get("last_login_at"),
        disabled_at=doc.get("disabled_at"),
    )


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
