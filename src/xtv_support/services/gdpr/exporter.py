"""GDPR data export.

Collects every collection where a user's id, tickets, or messages
appear and returns a JSON-serialisable dict. Exclusive to the user
who requested it — the handler looks them up via ``message.from_user.id``
and hands that to :func:`build_export`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from xtv_support.core.logger import get_logger
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

_log = get_logger("gdpr.export")


@dataclass(frozen=True, slots=True)
class ExportBundle:
    user_id: int
    generated_at: datetime
    sections: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at.isoformat(),
            "sections": {k: v for k, v in self.sections.items()},
        }


async def build_export(db: AsyncIOMotorDatabase, user_id: int) -> ExportBundle:
    """Assemble the export. Sections included:

    * ``user`` — the user's own doc from ``users``
    * ``tickets`` — every ticket where ``user_id`` matches
    * ``csat_responses`` — ratings / comments this user submitted
    * ``audit`` — audit entries mentioning this user id
    """
    sections: dict[str, list[dict[str, Any]]] = {}

    async def _collect(coll, query, section_name: str) -> None:
        try:
            rows = [_jsonable(doc) async for doc in coll.find(query)]
        except Exception as exc:  # noqa: BLE001
            _log.warning("gdpr.export.section_failed", section=section_name, error=str(exc))
            rows = []
        sections[section_name] = rows

    user_query = {"user_id": user_id}
    await _collect(db.users, user_query, "user")
    await _collect(db.tickets, {"user_id": user_id}, "tickets")
    await _collect(db.csat_responses, {"user_id": user_id}, "csat_responses")
    await _collect(
        db.audit_log,
        {"$or": [{"target_id": str(user_id)}, {"actor_id": user_id}]},
        "audit",
    )

    bundle = ExportBundle(
        user_id=user_id,
        generated_at=utcnow(),
        sections=sections,
    )
    _log.info(
        "gdpr.export.built",
        user_id=user_id,
        sections={k: len(v) for k, v in sections.items()},
    )
    return bundle


def _jsonable(doc: Any) -> dict[str, Any]:
    """Shallow-serialise a Mongo doc for JSON output."""
    if not isinstance(doc, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in doc.items():
        out[str(k)] = _jsonable_value(v)
    return out


def _jsonable_value(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [_jsonable_value(x) for x in v]
    if isinstance(v, dict):
        return _jsonable(v)
    # ObjectId -> str, falls through via repr for anything exotic.
    try:
        return str(v) if v is not None and not isinstance(v, (int, float, bool, str)) else v
    except Exception:  # noqa: BLE001
        return repr(v)
