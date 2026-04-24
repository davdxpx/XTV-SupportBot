"""System routes — /metrics + detailed readiness probe.

/health + /ready live directly in api/server.py; this module adds the
Prometheus exposition endpoint. Split out so toggling
``METRICS_ENABLED`` is a single mount point.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter
    from fastapi.responses import Response

    from xtv_support.infrastructure.metrics.registry import render_text

    router = APIRouter(tags=["system"])

    @router.get("/metrics")
    async def metrics() -> Response:
        body = render_text()
        return Response(
            content=body,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return router
