"""Exporter tests — CSV + JSON column contract."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from xtv_support.services.analytics.exporter import (
    COLUMNS,
    export_tickets_csv,
    export_tickets_json,
)


def _utc(y, m, d, H=0, M=0, S=0) -> datetime:
    return datetime(y, m, d, H, M, S, tzinfo=UTC)


def _ticket() -> dict:
    return {
        "_id": "t1",
        "user_id": 99,
        "project_id": "P1",
        "team_id": "support",
        "status": "closed",
        "priority": "normal",
        "tags": ["billing", "vip"],
        "created_at": _utc(2026, 4, 20, 10),
        "closed_at": _utc(2026, 4, 20, 12),
        "last_admin_msg_at": _utc(2026, 4, 20, 10, 5),
        "assignee_id": 42,
        "sentiment": "neutral",
    }


def test_columns_contract_is_stable() -> None:
    # Protect the header order — breaking this requires a version bump
    # of the export schema and coordinated client changes.
    assert COLUMNS[0] == "ticket_id"
    assert COLUMNS[-1] == "resolution_seconds"
    assert "csat_score" in COLUMNS


def test_json_export_produces_dicts_with_all_columns() -> None:
    rows = export_tickets_json([_ticket()])
    assert len(rows) == 1
    row = rows[0]
    assert set(row.keys()) == set(COLUMNS)
    assert row["ticket_id"] == "t1"
    assert row["tags"] == "billing,vip"
    assert row["first_response_seconds"] == str(5 * 60)
    assert row["resolution_seconds"] == str(2 * 3600)


def test_json_export_with_csat() -> None:
    rows = export_tickets_json([_ticket()], csat_by_ticket={"t1": 5})
    assert rows[0]["csat_score"] == "5"


def test_json_export_missing_fields_empty_string() -> None:
    rows = export_tickets_json([{"_id": "x"}])
    row = rows[0]
    assert row["status"] == ""
    assert row["first_response_seconds"] == ""


def test_csv_export_header_matches_columns() -> None:
    text = export_tickets_csv([])
    header_line = text.splitlines()[0]
    assert header_line.split(",") == list(COLUMNS)


def test_csv_export_round_trips_with_tickets() -> None:
    text = export_tickets_csv([_ticket()])
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["ticket_id"] == "t1"
    assert rows[0]["tags"] == "billing,vip"


def test_csv_export_handles_empty_iterable() -> None:
    text = export_tickets_csv([])
    # Only the header line (plus trailing newline).
    assert text.count("\n") == 1
