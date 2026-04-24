"""Analytics aggregator tests — pure, no DB required."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from xtv_support.services.analytics.aggregator import (
    compute_agent_leaderboard,
    compute_response_times,
    compute_sla_compliance,
    compute_volume,
)


def _utc(y, m, d, H=0, M=0, S=0) -> datetime:
    return datetime(y, m, d, H, M, S, tzinfo=UTC)


# ----------------------------------------------------------------------
# compute_volume
# ----------------------------------------------------------------------
def test_volume_empty() -> None:
    v = compute_volume([])
    assert v.total == 0
    assert v.by_day == {}


def test_volume_counts_every_dimension() -> None:
    tickets = [
        {
            "created_at": _utc(2026, 4, 20, 10),
            "project_id": "P1",
            "team_id": "support",
            "priority": "normal",
            "status": "open",
        },
        {
            "created_at": _utc(2026, 4, 20, 15),
            "project_id": "P1",
            "team_id": "support",
            "priority": "urgent",
            "status": "closed",
        },
        {
            "created_at": _utc(2026, 4, 21, 9),
            "project_id": "P2",
            "team_id": "billing",
            "priority": "normal",
            "status": "open",
        },
    ]
    v = compute_volume(tickets)
    assert v.total == 3
    assert v.by_day == {"2026-04-20": 2, "2026-04-21": 1}
    assert v.by_project == {"P1": 2, "P2": 1}
    assert v.by_team == {"support": 2, "billing": 1}
    assert v.by_priority == {"normal": 2, "urgent": 1}
    assert v.by_status == {"open": 2, "closed": 1}


def test_volume_skips_missing_created_at() -> None:
    tickets = [{"project_id": "P"}, {"created_at": "not a datetime"}]
    v = compute_volume(tickets)
    assert v.total == 2
    assert v.by_day == {}


# ----------------------------------------------------------------------
# compute_response_times
# ----------------------------------------------------------------------
def test_response_times_empty() -> None:
    r = compute_response_times([])
    assert r.samples == 0
    assert r.first_response_median is None
    assert r.resolution_median is None


def test_response_times_medians() -> None:
    base = _utc(2026, 4, 20, 10, 0)
    tickets = [
        # FRT 60s, resolved in 3600s
        {
            "created_at": base,
            "last_admin_msg_at": base + timedelta(seconds=60),
            "closed_at": base + timedelta(seconds=3600),
        },
        # FRT 180s, resolved in 7200s
        {
            "created_at": base,
            "last_admin_msg_at": base + timedelta(seconds=180),
            "closed_at": base + timedelta(seconds=7200),
        },
        # FRT 600s, unresolved (no closed_at)
        {
            "created_at": base,
            "last_admin_msg_at": base + timedelta(seconds=600),
        },
    ]
    r = compute_response_times(tickets)
    assert r.samples == 3
    assert r.first_response_median == 180  # middle value of [60, 180, 600]
    assert r.resolution_median == 5400  # mean of 3600 and 7200


def test_response_times_skips_missing_timestamps() -> None:
    r = compute_response_times([{"foo": "bar"}])
    assert r.samples == 1
    assert r.first_response_median is None


# ----------------------------------------------------------------------
# compute_sla_compliance
# ----------------------------------------------------------------------
def test_sla_empty() -> None:
    s = compute_sla_compliance([])
    assert s.total == 0
    assert s.compliance_ratio == 1.0


def test_sla_compliance_counts_breaches_on_close() -> None:
    base = _utc(2026, 4, 20, 10)
    tickets = [
        {
            "sla_deadline": base + timedelta(hours=1),
            "closed_at": base + timedelta(hours=2),
        },  # breached
        {
            "sla_deadline": base + timedelta(hours=1),
            "closed_at": base + timedelta(minutes=30),
        },  # met
        {"sla_deadline": base + timedelta(hours=1)},  # still open, deadline long past -> breached
    ]
    s = compute_sla_compliance(tickets)
    assert s.total == 3
    assert s.breached == 2


# ----------------------------------------------------------------------
# compute_agent_leaderboard
# ----------------------------------------------------------------------
def test_leaderboard_ranks_by_closed_count() -> None:
    base = _utc(2026, 4, 20, 10)
    tickets = [
        {
            "status": "closed",
            "assignee_id": 1,
            "created_at": base,
            "closed_at": base + timedelta(hours=1),
        },
        {
            "status": "closed",
            "assignee_id": 1,
            "created_at": base,
            "closed_at": base + timedelta(hours=3),
        },
        {
            "status": "closed",
            "assignee_id": 2,
            "created_at": base,
            "closed_at": base + timedelta(hours=2),
        },
        {"status": "open", "assignee_id": 3},  # open, skipped
    ]
    rows = compute_agent_leaderboard(tickets)
    assert len(rows) == 2
    assert rows[0].agent_id == 1 and rows[0].closed == 2
    assert rows[1].agent_id == 2 and rows[1].closed == 1
    assert rows[0].avg_resolution_seconds == (3600 + 10800) / 2


def test_leaderboard_uses_closed_by_when_assignee_missing() -> None:
    base = _utc(2026, 4, 20, 10)
    tickets = [
        {
            "status": "closed",
            "closed_by": 5,
            "created_at": base,
            "closed_at": base + timedelta(hours=1),
        },
    ]
    rows = compute_agent_leaderboard(tickets)
    assert len(rows) == 1 and rows[0].agent_id == 5


def test_leaderboard_includes_csat_averages() -> None:
    tickets = [
        {"status": "closed", "assignee_id": 1},
        {"status": "closed", "assignee_id": 2},
    ]
    rows = compute_agent_leaderboard(
        tickets,
        csat_by_agent={1: [5, 5, 4], 2: [2]},
    )
    by_id = {r.agent_id: r for r in rows}
    assert by_id[1].csat_average == round((5 + 5 + 4) / 3, 2)
    assert by_id[2].csat_average == 2.0


def test_leaderboard_top_limit() -> None:
    tickets = [{"status": "closed", "assignee_id": i} for i in range(15)]
    rows = compute_agent_leaderboard(tickets, top=5)
    assert len(rows) == 5
