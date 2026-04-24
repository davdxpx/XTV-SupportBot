"""Tests for the admin-SPA static mount on the FastAPI app."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a synthetic web/dist next to a fake repo root and point the
    settings at it. Returns the dist directory so tests can assert on its
    layout."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><html><body><div id="root"></div></body></html>'
    )
    (dist / "assets" / "app.js").write_text("console.log('spa');")
    (dist / "favicon.svg").write_text("<svg/>")

    # Point the server's repo-root anchor at tmp_path so it finds the
    # synthetic dist/ when WEB_DIST_DIR="dist".
    import xtv_support.api.server as srv

    monkeypatch.setattr(srv, "_REPO_ROOT", tmp_path)
    monkeypatch.setenv("WEB_DIST_DIR", "dist")
    monkeypatch.setenv("WEB_ENABLED", "true")

    # Reset the lru_cache on get_settings so the new env is observed.
    from xtv_support.config import settings as settings_mod

    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    return dist


def _create_test_app():
    from xtv_support.api.server import create_app

    return create_app(db=None)


def test_spa_serves_root_when_enabled(tmp_dist: Path) -> None:
    client = TestClient(_create_test_app())
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert b'id="root"' in r.content


def test_spa_fallback_survives_client_routing(tmp_dist: Path) -> None:
    """A deep-link like /tickets/abc must return the SPA shell, not 404.

    This is what makes React-Router deep-links survive a hard refresh.
    """
    client = TestClient(_create_test_app())
    r = client.get("/tickets/abc")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_api_paths_not_caught_by_spa(tmp_dist: Path) -> None:
    """/api/... must still return JSON 404s, not the SPA HTML."""
    client = TestClient(_create_test_app())
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    # FastAPI's 404 is JSON, never HTML.
    assert r.headers["content-type"].startswith("application/json")


def test_health_and_ready_still_json(tmp_dist: Path) -> None:
    client = TestClient(_create_test_app())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_favicon_served(tmp_dist: Path) -> None:
    client = TestClient(_create_test_app())
    r = client.get("/favicon.svg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg")


def test_spa_disabled_when_flag_off(tmp_dist: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEB_ENABLED", "false")
    from xtv_support.config import settings as settings_mod

    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    client = TestClient(_create_test_app())
    r = client.get("/")
    # With the SPA off, "/" is an undeclared route -> 404.
    assert r.status_code == 404
    r = client.get("/health")
    assert r.status_code == 200


def test_spa_skipped_when_dist_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No dist/index.html -> SPA mount silently skipped, API stays up."""
    import xtv_support.api.server as srv

    monkeypatch.setattr(srv, "_REPO_ROOT", tmp_path)
    monkeypatch.setenv("WEB_DIST_DIR", "nonexistent-dir")
    monkeypatch.setenv("WEB_ENABLED", "true")

    from xtv_support.config import settings as settings_mod

    settings_mod.get_settings.cache_clear()
    settings_mod.settings = settings_mod.get_settings()

    client = TestClient(_create_test_app())
    r = client.get("/")
    assert r.status_code == 404
    r = client.get("/health")
    assert r.status_code == 200
