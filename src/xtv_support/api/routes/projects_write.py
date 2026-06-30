"""Project write endpoints — create, edit, archive/restore, hard-delete.

POST /api/v1/projects accepts a ``template_slug`` to install one of the
built-in templates (Phase 4.2). If no ``template_slug`` is given, a
blank project with only the provided metadata is created.

Edit + lifecycle routes are keyed by ``_id`` (with a slug fallback for
back-compat). Archive/restore toggle ``active``; DELETE hard-removes the
project document. Tickets keep their ``project_id`` backreference — no
destructive cascade — so historical tickets survive a project purge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException

    from xtv_support.api.deps import get_db, require_scope
    from xtv_support.core.events import EventBus
    from xtv_support.infrastructure.db import projects as projects_repo
    from xtv_support.services.templates import default_registry, install_template
    from xtv_support.utils.time import utcnow

    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    @router.post("")
    async def create_project(
        body: dict = Body(...),
        db=Depends(get_db),
        key=Depends(require_scope("projects:write")),
    ) -> dict:
        # dict body (not a Pydantic model) — a locally-defined model under
        # ``from __future__ import annotations`` is misclassified as a query
        # param by FastAPI (CLAUDE.md gotcha → 422). Validate manually.
        project_slug = (body.get("project_slug") or "").strip()
        if not project_slug:
            raise HTTPException(status_code=400, detail="missing_project_slug")
        name = body.get("name")
        template_slug = body.get("template_slug")
        installed_by = key.created_by or 0
        if template_slug:
            template = default_registry.get(template_slug)
            if template is None:
                raise HTTPException(status_code=400, detail=f"unknown_template: {template_slug}")
            bus = EventBus()
            result = await install_template(
                db,
                bus,
                template=template,
                project_slug=project_slug,
                project_name=name,
                installed_by=installed_by,
            )
            if not result.ok:
                raise HTTPException(status_code=400, detail=result.detail or "install_failed")
            return {
                "ok": True,
                "project_id": result.project_id,
                "template_slug": template_slug,
                "macros_seeded": result.macros_seeded,
                "kb_articles_seeded": result.kb_articles_seeded,
                "routing_rules_seeded": result.routing_rules_seeded,
            }

        # Blank project
        existing = await db.projects.find_one({"slug": project_slug})
        if existing is not None:
            raise HTTPException(status_code=409, detail="project_slug_taken")
        insert = await db.projects.insert_one(
            {
                "slug": project_slug,
                "name": name or project_slug,
                "type": "support",
                "template_slug": None,
                "active": True,
                "created_at": utcnow(),
                "created_by": installed_by,
                "ticket_count": 0,
            }
        )
        return {"ok": True, "project_id": str(insert.inserted_id), "template_slug": None}

    async def _resolve(db, project_id: str) -> dict:
        doc = await projects_repo.get_by_id_or_slug(db, project_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="not_found")
        return doc

    @router.patch("/{project_id}")
    async def update_project(
        project_id: str,
        body: dict = Body(...),
        db=Depends(get_db),
        _key=Depends(require_scope("projects:write")),
    ) -> dict:
        doc = await _resolve(db, project_id)
        ok = await projects_repo.update(db, doc["_id"], body)
        if not ok:
            raise HTTPException(status_code=400, detail="no_editable_fields")
        return {"ok": True, "id": str(doc["_id"])}

    @router.post("/{project_id}/archive")
    async def archive_project(
        project_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("projects:write")),
    ) -> dict:
        doc = await _resolve(db, project_id)
        await db.projects.update_one(
            {"_id": doc["_id"]}, {"$set": {"active": False, "archived_at": utcnow()}}
        )
        return {"ok": True, "id": str(doc["_id"]), "active": False}

    @router.post("/{project_id}/restore")
    async def restore_project(
        project_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("projects:write")),
    ) -> dict:
        doc = await _resolve(db, project_id)
        await db.projects.update_one(
            {"_id": doc["_id"]}, {"$set": {"active": True}, "$unset": {"archived_at": ""}}
        )
        return {"ok": True, "id": str(doc["_id"]), "active": True}

    @router.delete("/{project_id}")
    async def delete_project(
        project_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("projects:write")),
    ) -> dict:
        # Hard delete. Tickets keep their project_id backreference (no
        # destructive cascade) so history survives.
        doc = await _resolve(db, project_id)
        await projects_repo.delete(db, doc["_id"])
        return {"ok": True, "id": str(doc["_id"]), "deleted": True}

    return router
