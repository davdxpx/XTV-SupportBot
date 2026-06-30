"""``/api/v1/macros`` + ``/api/v1/kb`` — web management for macros & KB.

Brings the bot's macro and knowledge-base surfaces to the admin console,
reusing :mod:`infrastructure.db.macros` and :mod:`infrastructure.db.kb`.
Owner/admin only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

_log = get_logger("api.content")


async def _require_manager(request: Request) -> None:
    from fastapi import HTTPException

    from xtv_support.api.deps import current_principal, get_db
    from xtv_support.api.security import ApiKey, scope_satisfies
    from xtv_support.config.settings import settings
    from xtv_support.core.rbac import resolve_role
    from xtv_support.domain.enums import Role
    from xtv_support.domain.models.admin_account import AdminAccount

    principal = await current_principal(request)
    db = await get_db(request)
    if isinstance(principal, AdminAccount):
        role = await resolve_role(
            db, principal.telegram_user_id, legacy_admin_ids=settings.ADMIN_IDS
        )
        if not role.can(Role.ADMIN):
            raise HTTPException(403, "insufficient_role")
        return
    if isinstance(principal, ApiKey) and scope_satisfies(principal.scopes, "admin:full"):
        return
    raise HTTPException(403, "insufficient_role")


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException

    from xtv_support.api.deps import get_db
    from xtv_support.infrastructure.db import kb as kb_repo
    from xtv_support.infrastructure.db import macros as macros_repo

    router = APIRouter(prefix="/api/v1", tags=["content"])

    def _macro_dict(m) -> dict:
        return {
            "id": m.id,
            "name": m.name,
            "body": m.body,
            "team_id": m.team_id,
            "tags": list(m.tags),
            "usage_count": m.usage_count,
        }

    def _kb_dict(a) -> dict:
        return {
            "id": a.id,
            "slug": a.slug,
            "title": a.title,
            "body": a.body,
            "lang": a.lang,
            "tags": list(a.tags),
            "project_ids": list(a.project_ids),
            "views": a.views,
        }

    # ---- Macros ------------------------------------------------------------
    @router.get("/macros")
    async def list_macros(db=Depends(get_db), _=Depends(_require_manager)) -> dict:
        items = [_macro_dict(m) for m in await macros_repo.list_all(db)]
        return {"items": items, "count": len(items)}

    @router.post("/macros", status_code=201)
    async def create_macro(
        body: dict = Body(...), db=Depends(get_db), _=Depends(_require_manager)
    ) -> dict:
        name = (body.get("name") or "").strip()
        text = body.get("body") or ""
        if not name or not text.strip():
            raise HTTPException(400, "name_and_body_required")
        try:
            m = await macros_repo.create(
                db,
                name=name,
                body=text,
                team_id=(body.get("team_id") or None),
                tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
                created_by=0,
            )
        except macros_repo.InvalidMacroNameError:
            raise HTTPException(400, "invalid_macro_name") from None
        except ValueError as exc:  # duplicate
            raise HTTPException(409, str(exc)) from exc
        return {"ok": True, "macro": _macro_dict(m)}

    @router.patch("/macros/{macro_id}")
    async def update_macro(
        macro_id: str, body: dict = Body(...), db=Depends(get_db), _=Depends(_require_manager)
    ) -> dict:
        text = body.get("body")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(400, "body_required")
        await macros_repo.update_body(db, macro_id, text)
        return {"ok": True}

    @router.delete("/macros/{macro_id}")
    async def delete_macro(macro_id: str, db=Depends(get_db), _=Depends(_require_manager)) -> dict:
        ok = await macros_repo.delete(db, macro_id)
        if not ok:
            raise HTTPException(404, "macro_not_found")
        return {"ok": True}

    # ---- Knowledge base ----------------------------------------------------
    @router.get("/kb")
    async def list_kb(db=Depends(get_db), _=Depends(_require_manager)) -> dict:
        items = [_kb_dict(a) for a in await kb_repo.list_all(db, limit=500)]
        return {"items": items, "count": len(items)}

    @router.post("/kb", status_code=201)
    async def create_kb(
        body: dict = Body(...), db=Depends(get_db), _=Depends(_require_manager)
    ) -> dict:
        slug = (body.get("slug") or "").strip()
        title = (body.get("title") or "").strip()
        text = body.get("body") or ""
        if not title or not text.strip():
            raise HTTPException(400, "title_and_body_required")
        try:
            a = await kb_repo.create(
                db,
                slug=slug,
                title=title,
                body=text,
                lang=(body.get("lang") or "en"),
                tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
                project_ids=body.get("project_ids")
                if isinstance(body.get("project_ids"), list)
                else None,
                created_by=0,
            )
        except kb_repo.InvalidSlugError:
            raise HTTPException(400, "invalid_slug") from None
        except ValueError as exc:  # duplicate slug
            raise HTTPException(409, str(exc)) from exc
        return {"ok": True, "article": _kb_dict(a)}

    @router.patch("/kb/{slug}")
    async def update_kb(
        slug: str, body: dict = Body(...), db=Depends(get_db), _=Depends(_require_manager)
    ) -> dict:
        ok = await kb_repo.update(
            db,
            slug,
            title=body.get("title"),
            body=body.get("body"),
            tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
            lang=body.get("lang"),
        )
        if not ok:
            raise HTTPException(404, "article_not_found")
        return {"ok": True}

    @router.delete("/kb/{slug}")
    async def delete_kb(slug: str, db=Depends(get_db), _=Depends(_require_manager)) -> dict:
        ok = await kb_repo.delete(db, slug)
        if not ok:
            raise HTTPException(404, "article_not_found")
        return {"ok": True}

    return router
