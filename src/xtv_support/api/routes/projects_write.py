"""Project write endpoints — create from template, archive.

POST /api/v1/projects accepts a ``template_slug`` to install one of the
built-in templates (Phase 4.2). If no ``template_slug`` is given, a
blank project with only the provided metadata is created.

DELETE /api/v1/projects/{slug} soft-archives (active=false) rather
than hard-deleting, so existing tickets keep their backreference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel

    from xtv_support.api.deps import get_db, require_scope
    from xtv_support.core.events import EventBus
    from xtv_support.services.templates import default_registry, install_template
    from xtv_support.utils.time import utcnow

    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    class ProjectCreatePayload(BaseModel):
        project_slug: str
        name: str | None = None
        template_slug: str | None = None

    @router.post("")
    async def create_project(
        body: ProjectCreatePayload,
        db=Depends(get_db),
        key=Depends(require_scope("projects:write")),
    ) -> dict:
        installed_by = key.created_by or 0
        if body.template_slug:
            template = default_registry.get(body.template_slug)
            if template is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"unknown_template: {body.template_slug}",
                )
            bus = EventBus()
            result = await install_template(
                db,
                bus,
                template=template,
                project_slug=body.project_slug,
                project_name=body.name,
                installed_by=installed_by,
            )
            if not result.ok:
                raise HTTPException(status_code=400, detail=result.detail or "install_failed")
            return {
                "ok": True,
                "project_id": result.project_id,
                "template_slug": body.template_slug,
                "macros_seeded": result.macros_seeded,
                "kb_articles_seeded": result.kb_articles_seeded,
                "routing_rules_seeded": result.routing_rules_seeded,
            }

        # Blank project
        existing = await db.projects.find_one({"slug": body.project_slug})
        if existing is not None:
            raise HTTPException(status_code=409, detail="project_slug_taken")
        insert = await db.projects.insert_one(
            {
                "slug": body.project_slug,
                "name": body.name or body.project_slug,
                "type": "support",
                "template_slug": None,
                "active": True,
                "created_at": utcnow(),
                "created_by": installed_by,
                "ticket_count": 0,
            }
        )
        return {"ok": True, "project_id": str(insert.inserted_id), "template_slug": None}

    @router.delete("/{project_slug}")
    async def archive_project(
        project_slug: str,
        db=Depends(get_db),
        _key=Depends(require_scope("projects:write")),
    ) -> dict:
        result = await db.projects.update_one(
            {"slug": project_slug},
            {"$set": {"active": False, "archived_at": utcnow()}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="not_found")
        return {"ok": True, "archived": project_slug}

    return router
