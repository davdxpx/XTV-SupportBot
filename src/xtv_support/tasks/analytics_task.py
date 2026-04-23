"""Nightly analytics rollup.

Runs once per configurable interval (default 24h) and writes per-day
aggregates into ``analytics_daily`` so the dashboards + digests can
query a tiny pre-computed collection instead of scanning every
ticket. Pure orchestration here — the heavy lifting is in
:mod:`xtv_support.services.analytics.aggregator`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.services.analytics.aggregator import (
    compute_response_times,
    compute_sla_compliance,
    compute_volume,
)

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

log = get_logger("analytics.task")

DEFAULT_LOOP_SECONDS = 3600        # re-check every hour; rollup runs once per UTC day


async def run_once(db: "AsyncIOMotorDatabase", *, for_date: datetime | None = None) -> None:
    """Compute aggregates for the day ending ``for_date`` (default: now - 1d).

    Stores one document per ``day`` key in the ``analytics_daily``
    collection. Upsert on ``{day}`` so re-runs are idempotent.
    """
    now = for_date or datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=1)
    day_key = start.date().isoformat()

    cursor = db.tickets.find(
        {
            "$or": [
                {"created_at": {"$gte": start, "$lt": end}},
                {"closed_at": {"$gte": start, "$lt": end}},
            ]
        }
    )
    tickets = [doc async for doc in cursor]
    if not tickets:
        log.debug("analytics.rollup.empty", day=day_key)
        return

    volume = compute_volume(tickets)
    rt = compute_response_times(tickets)
    sla = compute_sla_compliance(tickets)

    doc = {
        "day": day_key,
        "total": volume.total,
        "by_project": volume.by_project,
        "by_team": volume.by_team,
        "by_priority": volume.by_priority,
        "by_status": volume.by_status,
        "first_response_median": rt.first_response_median,
        "first_response_p90": rt.first_response_p90,
        "resolution_median": rt.resolution_median,
        "resolution_p90": rt.resolution_p90,
        "sla_breached": sla.breached,
        "sla_total": sla.total,
        "sla_compliance_ratio": sla.compliance_ratio,
        "generated_at": now,
    }
    try:
        await db.analytics_daily.update_one(
            {"day": day_key}, {"$set": doc}, upsert=True
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("analytics.rollup.write_failed", day=day_key, error=str(exc))
        return
    log.info(
        "analytics.rollup.done",
        day=day_key,
        tickets=volume.total,
        compliance=sla.compliance_ratio,
    )
