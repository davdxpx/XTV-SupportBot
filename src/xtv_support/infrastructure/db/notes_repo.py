"""Internal-notes repo.

Notes live inside the ticket document under ``internal_notes`` so a
single ``find_one`` on the ticket already returns them — no join, no
second round-trip. We deliberately store them in a field *separate*
from the public ``history`` array so that any code path that forwards
``history`` to the customer (past, present, future) cannot accidentally
leak a note.

A note is an append-only record:

    {"author_id": 123, "text": "...", "ts": datetime}
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorDatabase


def _coerce_oid(ticket_id: Any) -> Any:
    """Lazy-import bson.ObjectId so this module imports without pymongo."""
    try:
        from bson import ObjectId as _OID
    except ImportError:  # pragma: no cover — test/sandbox
        return ticket_id
    if isinstance(ticket_id, _OID):
        return ticket_id
    from xtv_support.utils.ids import safe_objectid

    return safe_objectid(ticket_id)


async def append_note(
    db: AsyncIOMotorDatabase,
    ticket_id: Any,
    *,
    author_id: int,
    text: str,
) -> dict[str, Any] | None:
    oid = _coerce_oid(ticket_id)
    if oid is None:
        return None
    note = {"author_id": author_id, "text": text, "ts": utcnow()}
    result = await db.tickets.update_one(
        {"_id": oid},
        {"$push": {"internal_notes": note}, "$set": {"updated_at": note["ts"]}},
    )
    if result.matched_count == 0:
        return None
    return note


async def list_notes(
    db: AsyncIOMotorDatabase,
    ticket_id: Any,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    oid = _coerce_oid(ticket_id)
    if oid is None:
        return []
    doc = await db.tickets.find_one({"_id": oid}, projection={"internal_notes": 1})
    notes = list((doc or {}).get("internal_notes") or [])
    if limit is not None:
        notes = notes[-limit:]
    return notes


async def count_notes(db: AsyncIOMotorDatabase, ticket_id: Any) -> int:
    notes = await list_notes(db, ticket_id)
    return len(notes)


def format_note_line(note: dict[str, Any]) -> str:
    ts: datetime | None = note.get("ts")
    stamp = ts.strftime("%Y-%m-%d %H:%M") if ts else "--"
    author = note.get("author_id", "?")
    text = str(note.get("text") or "").strip()
    return f"<i>[{stamp}]</i> <b>#{author}</b>: {text}"
