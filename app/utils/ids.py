from __future__ import annotations

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId


def safe_objectid(value: Any) -> ObjectId | None:
    """Return an ObjectId if ``value`` is a valid 24-hex id, else None."""
    if isinstance(value, ObjectId):
        return value
    if not isinstance(value, str):
        return None
    try:
        return ObjectId(value)
    except (InvalidId, TypeError, ValueError):
        return None


def short_ticket_id(oid: ObjectId | str) -> str:
    """Compact last-6-hex representation for display in topic titles / UI."""
    s = str(oid)
    return s[-6:] if len(s) >= 6 else s
