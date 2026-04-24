"""Automation-rules routes — read + write."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter, Body, Depends, HTTPException, Query

    from xtv_support.api.deps import get_db, require_scope
    from xtv_support.services.rules.repository import (
        create_rule,
        delete_rule,
        enable_rule,
        get_rule,
        list_rules,
    )

    router = APIRouter(prefix="/api/v1/rules", tags=["rules"])

    def _serialize(rule) -> dict:
        return {
            "id": rule.id,
            "name": rule.name,
            "enabled": rule.enabled,
            "trigger": rule.trigger,
            "cooldown_s": rule.cooldown_s,
            "conditions": [
                {"field": c.field, "op": c.op, "value": c.value} for c in rule.conditions
            ],
            "actions": [{"name": a.name, "params": a.params} for a in rule.actions],
            "version": rule.version,
        }

    @router.get("")
    async def list_all(
        db=Depends(get_db),
        _key=Depends(require_scope("rules:read")),
        enabled_only: bool = Query(False),
        trigger: str | None = Query(None),
        limit: int = Query(100, ge=1, le=500),
    ) -> dict:
        rules = await list_rules(db, enabled_only=enabled_only, trigger=trigger, limit=limit)
        return {"items": [_serialize(r) for r in rules], "count": len(rules)}

    @router.get("/{rule_id}")
    async def get_single(
        rule_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("rules:read")),
    ) -> dict:
        rule = await get_rule(db, rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail="not_found")
        return _serialize(rule)

    @router.post("", status_code=201)
    async def create(
        body: dict = Body(...),
        db=Depends(get_db),
        key=Depends(require_scope("rules:write")),
    ) -> dict:
        name = (body.get("name") or "").strip()
        trigger = (body.get("trigger") or "").strip()
        if not name or not trigger:
            raise HTTPException(status_code=400, detail="name_and_trigger_required")
        rule = await create_rule(
            db,
            name=name,
            trigger=trigger,
            conditions=body.get("conditions") or [],
            actions=body.get("actions") or [],
            cooldown_s=int(body.get("cooldown_s") or 0),
            enabled=bool(body.get("enabled", False)),
            created_by=getattr(key, "created_by", None),
        )
        return _serialize(rule)

    @router.patch("/{rule_id}/enabled")
    async def toggle(
        rule_id: str,
        body: dict = Body(...),
        db=Depends(get_db),
        _key=Depends(require_scope("rules:write")),
    ) -> dict:
        ok = await enable_rule(db, rule_id, bool(body.get("enabled", False)))
        if not ok:
            raise HTTPException(status_code=404, detail="not_found")
        return {"ok": True}

    @router.delete("/{rule_id}")
    async def delete(
        rule_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("rules:write")),
    ) -> dict:
        ok = await delete_rule(db, rule_id)
        if not ok:
            raise HTTPException(status_code=404, detail="not_found")
        return {"ok": True}

    return router
