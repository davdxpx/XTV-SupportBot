"""FastAPI application factory.

The app is built lazily (``create_app``) so importing
``xtv_support.api.server`` doesn't force a FastAPI install.
Bootstraps the health, ready, and version routes; other route
modules (tickets / projects / analytics / webhooks) are added here
as they arrive.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.version import __version__

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI

    from motor.motor_asyncio import AsyncIOMotorDatabase

_log = get_logger("api.server")


def create_app(
    *,
    db: "AsyncIOMotorDatabase | None" = None,
    title: str = "XTV-SupportBot API",
) -> "FastAPI":
    """Build a fresh FastAPI instance with the default route set."""
    try:
        from fastapi import FastAPI
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI not installed — install the `api` extra: pip install -e '.[api]'"
        ) from exc

    app = FastAPI(
        title=title,
        version=__version__,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )
    app.state.db = db

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"ok": True, "version": __version__}

    @app.get("/ready", tags=["system"])
    async def ready() -> dict:
        ok_db = True
        if db is not None:
            try:
                await db.command("ping")
            except Exception as exc:  # noqa: BLE001
                _log.warning("api.ready.db_ping_failed", error=str(exc))
                ok_db = False
        return {"ok": ok_db, "db": ok_db}

    @app.get("/api/v1/version", tags=["system"])
    async def version() -> dict:
        return {"version": __version__, "name": "XTV-SupportBot"}

    _log.info("api.app_created", version=__version__)
    return app
