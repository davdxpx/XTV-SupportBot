"""``/api/v1/me`` — Telegram user-scoped endpoints for the Mini-App.

Authenticated via the ``X-Telegram-Init-Data`` header (signed by the
bot token, validated in :mod:`xtv_support.api.auth_webapp`). The
whole namespace is **self-scoped** — a caller can only read and
modify their own tickets / settings. The admin SPA uses the legacy
``/api/v1/tickets``, ``/api/v1/projects`` routes with API-key auth.

Covered here (Phase 2):

* ``GET  /me``                    — profile + admin flag + ui_mode
* ``GET  /me/tickets``            — caller's tickets with status filter
* ``GET  /me/tickets/{id}``       — single ticket incl. history
* ``POST /me/tickets``            — create a new ticket
* ``POST /me/tickets/{id}/reply`` — add a user reply
* ``POST /me/tickets/{id}/close`` — self-close an open ticket
* ``GET  /me/projects``           — active projects available for intake
* ``GET  /me/settings``           — read my preferences
* ``PATCH /me/settings``          — update language + notification toggles
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xtv_support.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

# Module-level import so the ``request: Request`` annotation on get_me
# resolves via get_type_hints() — without ``from __future__ import
# annotations`` would lazy-stringify the hint and FastAPI would treat
# it as a query parameter (loc=["query","request"] → 422).
from fastapi import Request

_log = get_logger("api.me")


def _resolve_bot_client(request: Request):
    """Return the pyrofork Client from the app container, or None.

    FastAPI runs in the same process as the bot, which registers its Client in
    the DI container at boot. Resolution is best-effort: an API-only deploy (no
    bot, pyrogram absent) simply gets None and the caller degrades gracefully.
    """
    container = getattr(request.app.state, "container", None)
    if container is None:
        return None
    try:
        from pyrogram import Client

        return container.resolve(Client)
    except Exception as exc:  # noqa: BLE001 — any resolution/import failure → degrade
        _log.debug("api.me.client_unavailable", error=str(exc))
        return None


# Dispatcher-friendly projection — keeps documents slim on the wire.
def _ticket_summary(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "status": doc.get("status"),
        "priority": doc.get("priority"),
        "tags": doc.get("tags") or [],
        "project_id": str(doc["project_id"]) if doc.get("project_id") else None,
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
        "closed_at": doc.get("closed_at").isoformat() if doc.get("closed_at") else None,
        "last_user_msg_at": (
            doc["last_user_msg_at"].isoformat() if doc.get("last_user_msg_at") else None
        ),
        "last_admin_msg_at": (
            doc["last_admin_msg_at"].isoformat() if doc.get("last_admin_msg_at") else None
        ),
        "subject": (doc.get("message") or "")[:80],
        "is_vip": None,
        "tier_label": None,
        "display_badge": None,
    }


def _ticket_detail(doc: dict[str, Any]) -> dict[str, Any]:
    summary = _ticket_summary(doc)
    history = []
    for entry in doc.get("history") or []:
        ts = entry.get("timestamp")
        # Drop internal notes — those are never shown to the ticket owner.
        if entry.get("sender") == "internal":
            continue
        history.append(
            {
                "sender": entry.get("sender"),
                "text": entry.get("text"),
                "type": entry.get("type") or "text",
                "timestamp": ts.isoformat() if ts else None,
            }
        )
    summary["history"] = history
    return summary


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException, Query

    from xtv_support.api.auth_webapp import TelegramUser, current_tg_user
    from xtv_support.api.deps import current_principal, get_db
    from xtv_support.api.security import ApiKey, scope_satisfies
    from xtv_support.config.settings import settings
    from xtv_support.core.rbac import resolve_role
    from xtv_support.domain.enums import Role
    from xtv_support.domain.models.admin_account import AdminAccount
    from xtv_support.infrastructure.db import projects as projects_repo
    from xtv_support.infrastructure.db import tickets as tickets_repo
    from xtv_support.infrastructure.db import users as users_repo
    from xtv_support.utils.ids import safe_objectid

    router = APIRouter(prefix="/api/v1/me", tags=["me"])

    def _envelope(**over: Any) -> dict:
        base = {
            "id": 0,
            "first_name": "",
            "last_name": None,
            "username": None,
            "language_code": None,
            "is_admin": False,
            "role": None,
            "ui_mode": settings.ui_mode.value,
            "brand_name": settings.BRAND_NAME,
            "brand_tagline": settings.BRAND_TAGLINE,
        }
        base.update(over)
        return base

    @router.get("")
    async def get_me(request: Request) -> dict:
        principal = await current_principal(request)

        # Telegram Mini-App user — admin flag from ADMIN_IDS (unchanged).
        if isinstance(principal, TelegramUser):
            return _envelope(
                id=principal.id,
                first_name=principal.first_name,
                last_name=principal.last_name,
                username=principal.username,
                language_code=principal.language_code,
                is_admin=principal.id in set(settings.ADMIN_IDS),
            )

        # Real admin account — resolve permissions from the EXISTING Role
        # system (ADMIN_IDS-aware via resolve_role). AGENT+ may open the SPA.
        if isinstance(principal, AdminAccount):
            db = await get_db(request)
            role = await resolve_role(
                db, principal.telegram_user_id, legacy_admin_ids=settings.ADMIN_IDS
            )
            return _envelope(
                id=principal.telegram_user_id,
                first_name=principal.first_name,
                last_name=principal.last_name,
                username=principal.display_username,
                is_admin=role.can(Role.AGENT),
                role=str(role),
            )

        # Legacy API-key session — is_admin ONLY when scopes grant admin:full.
        key: ApiKey = principal
        return _envelope(
            id=key.created_by or 0,
            first_name=key.label or "Admin",
            is_admin=scope_satisfies(key.scopes, "admin:full"),
        )

    # ------------------------------------------------------------------
    # Projects for intake
    # ------------------------------------------------------------------
    @router.get("/projects")
    async def my_projects(
        user: TelegramUser = Depends(current_tg_user),
        db=Depends(get_db),
    ) -> dict:
        del user  # auth only — every Telegram user can see the intake list
        docs = await projects_repo.list_active(db)
        items = []
        for p in docs:
            items.append(
                {
                    "id": str(p.get("_id")),
                    "slug": p.get("slug"),
                    "name": p.get("name"),
                    "description": p.get("description"),
                    "type": p.get("type"),
                }
            )
        return {"items": items, "count": len(items)}

    # ------------------------------------------------------------------
    # Tickets — list + detail
    # ------------------------------------------------------------------
    @router.get("/tickets")
    async def my_tickets(
        user: TelegramUser = Depends(current_tg_user),
        db=Depends(get_db),
        status: str | None = Query(
            default=None,
            description="open | waiting | closed — omit for all",
        ),
        limit: int = Query(default=20, ge=1, le=100),
    ) -> dict:
        docs = await tickets_repo.list_by_user(db, user.id, limit=limit)
        if status:
            wanted = status.lower()
            if wanted == "waiting":
                # Waiting-on-user = open + last message was from admin.
                docs = [
                    d
                    for d in docs
                    if d.get("status") == "open" and d.get("last_admin_msg_at") is not None
                ]
            elif wanted == "open":
                docs = [d for d in docs if d.get("status") == "open"]
            elif wanted == "closed":
                docs = [d for d in docs if d.get("status") == "closed"]
        items = [_ticket_summary(d) for d in docs]
        return {"items": items, "count": len(items)}

    @router.get("/tickets/{ticket_id}")
    async def my_ticket(
        ticket_id: str,
        user: TelegramUser = Depends(current_tg_user),
        db=Depends(get_db),
    ) -> dict:
        doc = await tickets_repo.get(db, ticket_id)
        if doc is None or doc.get("user_id") != user.id:
            raise HTTPException(status_code=404, detail="ticket_not_found")
        return _ticket_detail(doc)

    # ------------------------------------------------------------------
    # Tickets — create / reply / close
    # ------------------------------------------------------------------
    @router.post("/tickets", status_code=201)
    async def create_my_ticket(
        request: Request,
        user: TelegramUser = Depends(current_tg_user),
        body: dict = Body(...),
        db=Depends(get_db),
    ) -> dict:
        message = (body.get("message") or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="empty_message")
        if len(message) > 4000:
            raise HTTPException(status_code=400, detail="message_too_long")
        project_raw = body.get("project_id") or body.get("project_slug")
        proj = None
        if project_raw:
            oid = safe_objectid(project_raw)
            if oid is None:
                proj = await db.projects.find_one({"slug": project_raw, "active": True})
            else:
                proj = await db.projects.find_one({"_id": oid, "active": True})
            if proj is None:
                raise HTTPException(status_code=404, detail="project_not_found")

        # Create through the shared ticket service so the web path produces the
        # SAME result as the bot: a forum topic + header card in the admin
        # supergroup, the forwarded message, and a user confirmation. The bot
        # Client lives in the container of the same process (FastAPI runs
        # alongside pyrofork). If it isn't available (API-only deploy), degrade
        # to a bare ticket insert so the endpoint still works.
        client = _resolve_bot_client(request)
        if client is not None:
            from xtv_support.services.tickets import service as ticket_service

            ticket = await ticket_service.create_ticket(
                client,
                db,
                user_id=user.id,
                user_name=user.first_name or user.username or f"User {user.id}",
                username=user.username,
                project=proj,
                text=message,
            )
            tid = ticket.get("_id")
        else:
            _log.warning("api.me.ticket_no_client", user_id=user.id)
            tid = await tickets_repo.create(
                db,
                project_id=str(proj["_id"]) if proj else None,
                user_id=user.id,
                message=message,
            )
        if tid is None:
            raise HTTPException(status_code=500, detail="ticket_create_failed")
        _log.info(
            "api.me.ticket_created",
            ticket_id=str(tid),
            user_id=user.id,
            project_id=str(proj["_id"]) if proj else None,
        )
        return {"id": str(tid), "status": "open"}

    @router.post("/tickets/{ticket_id}/reply")
    async def reply_my_ticket(
        ticket_id: str,
        user: TelegramUser = Depends(current_tg_user),
        body: dict = Body(...),
        db=Depends(get_db),
    ) -> dict:
        text = (body.get("message") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="empty_message")
        if len(text) > 4000:
            raise HTTPException(status_code=400, detail="message_too_long")
        doc = await tickets_repo.get(db, ticket_id)
        if doc is None or doc.get("user_id") != user.id:
            raise HTTPException(status_code=404, detail="ticket_not_found")
        if doc.get("status") != "open":
            raise HTTPException(status_code=409, detail="ticket_closed")
        await tickets_repo.append_history(
            db,
            doc["_id"],
            sender="user",
            text=text,
        )
        _log.info("api.me.ticket_reply", ticket_id=ticket_id, user_id=user.id)
        return {"ok": True}

    @router.post("/tickets/{ticket_id}/close")
    async def close_my_ticket(
        ticket_id: str,
        user: TelegramUser = Depends(current_tg_user),
        body: dict = Body(default_factory=dict),
        db=Depends(get_db),
    ) -> dict:
        doc = await tickets_repo.get(db, ticket_id)
        if doc is None or doc.get("user_id") != user.id:
            raise HTTPException(status_code=404, detail="ticket_not_found")
        if doc.get("status") != "open":
            return {"ok": True, "already_closed": True}
        reason = (body.get("reason") or "").strip() or "self_closed"
        await tickets_repo.close(db, doc["_id"], closed_by=user.id, reason=reason)
        _log.info("api.me.ticket_closed", ticket_id=ticket_id, user_id=user.id)
        return {"ok": True}

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    @router.get("/settings")
    async def my_settings(
        user: TelegramUser = Depends(current_tg_user),
        db=Depends(get_db),
    ) -> dict:
        doc = await users_repo.get(db, user.id) or {}
        prefs = doc.get("notification_prefs") or {}
        return {
            "language": doc.get("lang") or user.language_code or settings.DEFAULT_LANG,
            "ui_pref": doc.get("ui_pref"),
            "notify_on_reply": bool(prefs.get("notify_reply", True)),
            "notify_csat": bool(prefs.get("notify_csat", True)),
            "notify_announcements": bool(prefs.get("notify_announcements", True)),
        }

    @router.patch("/settings")
    async def update_my_settings(
        user: TelegramUser = Depends(current_tg_user),
        body: dict = Body(...),
        db=Depends(get_db),
    ) -> dict:
        """Partial update — only keys present in the body are touched."""
        set_ops: dict[str, Any] = {}
        if "language" in body:
            code = str(body["language"] or "").strip().lower()
            if not code or len(code) > 10:
                raise HTTPException(status_code=400, detail="bad_language")
            set_ops["lang"] = code
        if "ui_pref" in body:
            from xtv_support.core.ui_mode import UIMode

            pref = body["ui_pref"]
            if pref is None:
                set_ops["ui_pref"] = None
            else:
                set_ops["ui_pref"] = UIMode.parse(str(pref)).value
        prefs_patch: dict[str, Any] = {}
        for key in ("notify_on_reply", "notify_csat", "notify_announcements"):
            db_key = "notify_reply" if key == "notify_on_reply" else key
            if key in body:
                prefs_patch[f"notification_prefs.{db_key}"] = bool(body[key])
        if prefs_patch:
            set_ops.update(prefs_patch)
        if not set_ops:
            return {"ok": True, "changed": 0}
        await db.users.update_one(
            {"user_id": user.id},
            {"$set": set_ops, "$setOnInsert": {"user_id": user.id}},
            upsert=True,
        )
        _log.info("api.me.settings_updated", user_id=user.id, keys=list(set_ops.keys()))
        return {"ok": True, "changed": len(set_ops)}

    return router
