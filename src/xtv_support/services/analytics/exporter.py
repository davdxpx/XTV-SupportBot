"""CSV / JSON exporters for analytics.

Two call patterns:

* :func:`export_tickets_csv(iterable)` → streaming string (consumers
  write chunks to a temp file / HTTP response).
* :func:`export_tickets_json(iterable)` → list of plain dicts ready
  for ``json.dumps``.

Both operate over the same *column contract* so the output is stable
across entry points (Telegram ``/export``, REST API, digest archives).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping
from datetime import datetime

COLUMNS: tuple[str, ...] = (
    "ticket_id",
    "user_id",
    "project_id",
    "team_id",
    "status",
    "priority",
    "tags",
    "created_at",
    "closed_at",
    "assignee_id",
    "sentiment",
    "csat_score",
    "first_response_seconds",
    "resolution_seconds",
)


def _iso(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return "" if value is None else str(value)


def _duration(start, end) -> str:
    if isinstance(start, datetime) and isinstance(end, datetime):
        return str(int((end - start).total_seconds()))
    return ""


def _row(ticket: Mapping, *, csat_by_ticket: Mapping[str, int] | None = None) -> dict[str, str]:
    tid = str(ticket.get("_id") or "")
    created = ticket.get("created_at")
    closed = ticket.get("closed_at")
    first_admin = ticket.get("last_admin_msg_at")
    csat = (csat_by_ticket or {}).get(tid)
    return {
        "ticket_id": tid,
        "user_id": str(ticket.get("user_id") or ""),
        "project_id": str(ticket.get("project_id") or ""),
        "team_id": str(ticket.get("team_id") or ""),
        "status": str(ticket.get("status") or ""),
        "priority": str(ticket.get("priority") or ""),
        "tags": ",".join(ticket.get("tags") or ()),
        "created_at": _iso(created),
        "closed_at": _iso(closed),
        "assignee_id": str(ticket.get("assignee_id") or ""),
        "sentiment": str(ticket.get("sentiment") or ""),
        "csat_score": "" if csat is None else str(csat),
        "first_response_seconds": _duration(created, first_admin),
        "resolution_seconds": _duration(created, closed),
    }


def export_tickets_csv(
    tickets: Iterable[Mapping],
    *,
    csat_by_ticket: Mapping[str, int] | None = None,
) -> str:
    """Render an in-memory CSV string (suitable for small/medium exports)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for t in tickets:
        writer.writerow(_row(t, csat_by_ticket=csat_by_ticket))
    return buf.getvalue()


def export_tickets_json(
    tickets: Iterable[Mapping],
    *,
    csat_by_ticket: Mapping[str, int] | None = None,
) -> list[dict[str, str]]:
    return [_row(t, csat_by_ticket=csat_by_ticket) for t in tickets]
