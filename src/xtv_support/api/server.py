"""FastAPI application factory.

The app is built lazily (``create_app``) so importing
``xtv_support.api.server`` doesn't force a FastAPI install.
Bootstraps the health, ready, and version routes; other route
modules (tickets / projects / analytics / webhooks) are added here
as they arrive.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.version import __version__

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI
    from motor.motor_asyncio import AsyncIOMotorDatabase

_log = get_logger("api.server")

# Repo root — four parents up from this file (src/xtv_support/api/server.py).
_REPO_ROOT = Path(__file__).resolve().parents[3]


def create_app(
    *,
    db: AsyncIOMotorDatabase | None = None,
    title: str = "XTV-SupportBot API",
) -> FastAPI:
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

    # Mount core routers lazily so a user importing ``create_app`` in a
    # test environment that stubs out the routes doesn't pay for them.
    from xtv_support.api.routes import analytics as analytics_routes
    from xtv_support.api.routes import projects as projects_routes
    from xtv_support.api.routes import projects_write as projects_write_routes
    from xtv_support.api.routes import rules as rules_routes
    from xtv_support.api.routes import tickets as tickets_routes
    from xtv_support.api.routes import tickets_write as tickets_write_routes
    from xtv_support.api.routes import webhooks as webhooks_routes

    app.include_router(tickets_routes.build_router())
    app.include_router(tickets_write_routes.build_router())
    app.include_router(projects_routes.build_router())
    app.include_router(projects_write_routes.build_router())
    app.include_router(analytics_routes.build_router())
    app.include_router(rules_routes.build_router())
    app.include_router(webhooks_routes.build_router())

    _mount_spa(app)

    _log.info("api.app_created", version=__version__)
    return app


def _mount_spa(app: FastAPI) -> None:
    """Serve the React admin SPA at ``/`` when it has been built.

    Layout:
        ``web/dist/index.html`` is served as the root document; every
        other route that doesn't match an API path falls back to
        ``index.html`` so React-Router deep-links survive a hard
        refresh (e.g. ``/tickets/abc`` returns the SPA shell and
        React-Router picks up the path on the client).

    If ``WEB_ENABLED=false`` or the build output is missing (common
    in local dev when the TypeScript build hasn't run yet), the SPA
    mount is skipped silently and the API stays reachable on its
    normal paths.
    """
    from xtv_support.config.settings import settings

    if not getattr(settings, "WEB_ENABLED", True):
        _log.info("api.spa_disabled", reason="WEB_ENABLED=false")
        return

    dist_dir = _REPO_ROOT / getattr(settings, "WEB_DIST_DIR", "web/dist")
    index_html = dist_dir / "index.html"
    if not index_html.exists():
        _log.info(
            "api.spa_skipped",
            reason="web/dist/index.html missing — run `cd web && npm run build`",
            looked_in=str(dist_dir),
        )
        return

    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="spa_assets")

    @app.get("/favicon.svg", include_in_schema=False)
    async def _favicon_svg() -> FileResponse:
        fav = dist_dir / "favicon.svg"
        if fav.exists():
            return FileResponse(str(fav), media_type="image/svg+xml")
        raise HTTPException(status_code=404)

    # Catch-all SPA fallback. Registered LAST so every explicit API +
    # system route wins. Paths starting with ``api/``, ``health``,
    # ``ready`` are excluded via the regex and fall through to 404.
    _RESERVED_PREFIXES = ("api/", "health", "ready", "assets/", "favicon.")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(_RESERVED_PREFIXES):
            raise HTTPException(status_code=404)
        return FileResponse(str(index_html), media_type="text/html")

    _log.info("api.spa_mounted", dist_dir=str(dist_dir))
