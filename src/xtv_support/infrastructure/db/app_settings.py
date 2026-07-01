"""Runtime settings store.

Operational knobs that were previously env-only live here as overrides on the
``admin_overrides`` collection (doc ``_id="settings"``, values under a
``values`` sub-document). Env stays the source of defaults; anything absent
here falls back to the env value via :mod:`xtv_support.config.runtime`.
Secrets and infra settings are deliberately NOT stored here.
"""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from xtv_support.utils.time import utcnow

_DOC_ID = "settings"


async def get_overrides(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    doc = await db.admin_overrides.find_one({"_id": _DOC_ID})
    return dict((doc or {}).get("values") or {})


async def set_overrides(db: AsyncIOMotorDatabase, mapping: dict[str, Any]) -> None:
    if not mapping:
        return
    sets: dict[str, Any] = {f"values.{k}": v for k, v in mapping.items()}
    sets["updated_at"] = utcnow()
    await db.admin_overrides.update_one({"_id": _DOC_ID}, {"$set": sets}, upsert=True)


async def clear_override(db: AsyncIOMotorDatabase, key: str) -> None:
    await db.admin_overrides.update_one({"_id": _DOC_ID}, {"$unset": {f"values.{key}": ""}})
