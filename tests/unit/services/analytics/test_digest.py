"""Analytics digest renderer tests."""
from __future__ import annotations

from xtv_support.services.analytics.digest import DigestPayload, render


def test_empty_rollups() -> None:
    p = render([])
    assert "No tickets" in p.body
    assert "📊" in p.full_html


def test_single_rollup_rendering() -> None:
    rollups = [
        {
            "day": "2026-04-20",
            "total": 50,
            "sla_breached": 2,
            "sla_total": 48,
            "first_response_median": 120.0,
            "resolution_median": 3600.0,
            "by_project": {"P1": 30, "P2": 20},
            "by_team": {"support": 40, "billing": 10},
        }
    ]
    p = render(rollups)
    assert "Tickets</b>: 50" in p.body
    assert "SLA compliance" in p.body
    # 2 breached of 48 -> 46/48 met, ratio ~= 96%
    assert "96%" in p.body
    assert "2m" in p.body             # FRT 120s -> 2m
    assert "1.0h" in p.body           # resolution 3600s -> 1.0h
    assert "P1" in p.body and "support" in p.body


def test_multi_rollup_totals_are_summed() -> None:
    rollups = [
        {
            "day": "2026-04-20", "total": 10, "sla_breached": 1, "sla_total": 10,
            "by_project": {"P1": 10}, "by_team": {},
            "first_response_median": 60.0, "resolution_median": 1800.0,
        },
        {
            "day": "2026-04-21", "total": 20, "sla_breached": 3, "sla_total": 20,
            "by_project": {"P1": 15, "P2": 5}, "by_team": {},
            "first_response_median": 120.0, "resolution_median": 7200.0,
        },
    ]
    p = render(rollups, for_range="last 2 days")
    assert "Tickets</b>: 30" in p.body
    # 4 breached / 30 total -> 87%
    assert "87%" in p.body
    # P1 aggregated: 25
    assert "P1" in p.body and "25" in p.body
    assert "last 2 days" in p.title


def test_digest_payload_full_html_shape() -> None:
    p = DigestPayload(title="T", body="B")
    assert p.full_html == "<b>T</b>\n\nB"
