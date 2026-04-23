"""Analytics routes — read from the rollup collection."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> "APIRouter":
    from fastapi import APIRouter, Depends, Query

    from xtv_support.api.deps import get_db, require_scope

    router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

    @router.get("/summary")
    async def summary(
        db=Depends(get_db),
        _key=Depends(require_scope("analytics:read")),
        days: int = Query(7, ge=1, le=365),
    ) -> dict:
        cursor = db.analytics_daily.find().sort("day", -1).limit(days)
        rollups = [d async for d in cursor]
        total = sum(int(d.get("total", 0)) for d in rollups)
        breached = sum(int(d.get("sla_breached", 0)) for d in rollups)
        sla_total = sum(int(d.get("sla_total", 0)) for d in rollups)
        ratio = 1.0 if sla_total == 0 else 1 - (breached / sla_total)
        return {
            "days": days,
            "tickets": total,
            "sla_breached": breached,
            "sla_total": sla_total,
            "sla_compliance_ratio": round(ratio, 3),
            "rollups": rollups,
        }

    return router
