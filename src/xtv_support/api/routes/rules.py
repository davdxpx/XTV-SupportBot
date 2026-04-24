"""Read-only automation-rules routes (Phase 4.6).

Write endpoints land in a follow-up; the bot UI in
:mod:`xtv_support.handlers.admin.rules` covers every mutation today.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter


def build_router() -> APIRouter:
    from fastapi import APIRouter, Depends, HTTPException, Query

    from xtv_support.api.deps import get_db, require_scope
    from xtv_support.services.rules.repository import get_rule, list_rules

    router = APIRouter(prefix="/api/v1/rules", tags=["rules"])

    @router.get("")
    async def list_all(
        db=Depends(get_db),
        _key=Depends(require_scope("rules:read")),
        enabled_only: bool = Query(False),
        trigger: str | None = Query(None),
        limit: int = Query(100, ge=1, le=500),
    ) -> dict:
        rules = await list_rules(
            db, enabled_only=enabled_only, trigger=trigger, limit=limit
        )
        items = [
            {
                "id": r.id,
                "name": r.name,
                "enabled": r.enabled,
                "trigger": r.trigger,
                "cooldown_s": r.cooldown_s,
                "conditions": [
                    {"field": c.field, "op": c.op, "value": c.value}
                    for c in r.conditions
                ],
                "actions": [{"name": a.name, "params": a.params} for a in r.actions],
                "version": r.version,
            }
            for r in rules
        ]
        return {"items": items, "count": len(items)}

    @router.get("/{rule_id}")
    async def get_single(
        rule_id: str,
        db=Depends(get_db),
        _key=Depends(require_scope("rules:read")),
    ) -> dict:
        rule = await get_rule(db, rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail="not_found")
        return {
            "id": rule.id,
            "name": rule.name,
            "enabled": rule.enabled,
            "trigger": rule.trigger,
            "cooldown_s": rule.cooldown_s,
            "conditions": [
                {"field": c.field, "op": c.op, "value": c.value}
                for c in rule.conditions
            ],
            "actions": [{"name": a.name, "params": a.params} for a in rule.actions],
            "version": rule.version,
        }

    return router
