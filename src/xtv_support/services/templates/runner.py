"""Apply a :class:`ProjectTemplate` to a fresh project.

The runner writes to Mongo:

- inserts a project document (if one with that slug doesn't exist yet)
- seeds macros, KB articles, routing rules
- applies SLA overrides + CSAT config
- emits :class:`ProjectTemplateInstalled` (or ``Failed``)

It intentionally does *not* touch feature flags — flags are env-level
defaults. Per-project overrides land in a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xtv_support.core.events import EventBus
from xtv_support.core.logger import get_logger
from xtv_support.domain.events.templates import (
    ProjectTemplateFailed,
    ProjectTemplateInstalled,
)
from xtv_support.services.templates.model import ProjectTemplate
from xtv_support.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

log = get_logger("templates.runner")


@dataclass(slots=True)
class InstallResult:
    ok: bool
    project_id: str | None = None
    detail: str | None = None
    macros_seeded: int = 0
    kb_articles_seeded: int = 0
    routing_rules_seeded: int = 0
    warnings: tuple[str, ...] = ()


async def install_template(
    db: AsyncIOMotorDatabase,
    bus: EventBus,
    *,
    template: ProjectTemplate,
    project_slug: str,
    project_name: str | None = None,
    installed_by: int,
) -> InstallResult:
    """Create a new project from ``template``. Idempotent on ``project_slug``."""
    warnings: list[str] = []
    name = project_name or template.name

    try:
        existing = await db.projects.find_one({"slug": project_slug})
        if existing is not None:
            return InstallResult(
                ok=False,
                detail="project_slug_taken",
                project_id=str(existing.get("_id")),
            )

        now = utcnow()
        project_doc = {
            "slug": project_slug,
            "name": name,
            "description": template.description,
            "type": template.project_type,
            "template_slug": template.slug,
            "active": True,
            "default_priority": template.default_priority,
            "default_tags": list(template.default_tags),
            "csat_enabled": template.csat_enabled,
            "csat_required": template.csat_required,
            "sla_warn_minutes": template.sla_overrides.warn_minutes
            if template.sla_overrides
            else None,
            "sla_breach_minutes": template.sla_overrides.breach_minutes
            if template.sla_overrides
            else None,
            "welcome_card_title": template.welcome_card_title,
            "welcome_card_body": template.welcome_card_body,
            "intake_fields": list(template.intake_fields),
            "created_at": now,
            "created_by": installed_by,
            "ticket_count": 0,
        }
        insert = await db.projects.insert_one(project_doc)
        project_id = insert.inserted_id

        macros_seeded = 0
        for m in template.macros:
            await db.macros.update_one(
                {"name": m.name, "team_id": m.team_scope},
                {
                    "$setOnInsert": {
                        "name": m.name,
                        "body": m.body,
                        "tags": list(m.tags),
                        "team_id": m.team_scope,
                        "project_id": project_id,
                        "created_at": now,
                        "created_by": installed_by,
                        "usage_count": 0,
                    }
                },
                upsert=True,
            )
            macros_seeded += 1

        kb_seeded = 0
        for k in template.kb_articles:
            slug = f"{project_slug}__{k.slug}"
            await db.kb_articles.update_one(
                {"slug": slug},
                {
                    "$setOnInsert": {
                        "slug": slug,
                        "title": k.title,
                        "body": k.body,
                        "tags": list(k.tags),
                        "lang": k.lang,
                        "project_ids": [project_id],
                        "created_at": now,
                        "created_by": installed_by,
                    }
                },
                upsert=True,
            )
            kb_seeded += 1

        routing_seeded = 0
        if template.routing_rules:
            # Store the seeded rules on the project so an admin can view
            # them later; actual team-side application happens in the
            # routing dispatcher (see services/teams/routing.py).
            serialised = [
                {
                    "match_tag": r.match_tag,
                    "match_priority": r.match_priority,
                    "match_project_type": r.match_project_type,
                    "weight": r.weight,
                    "target_team_slug": r.target_team_slug,
                }
                for r in template.routing_rules
            ]
            await db.projects.update_one(
                {"_id": project_id},
                {"$set": {"seeded_routing_rules": serialised}},
            )
            routing_seeded = len(serialised)

        if template.feature_flag_overrides:
            warnings.append(
                "feature_flag_overrides stored on project; live-toggle arrives in 4.4"
            )
            await db.projects.update_one(
                {"_id": project_id},
                {"$set": {"feature_flag_overrides": dict(template.feature_flag_overrides)}},
            )

        await bus.publish(
            ProjectTemplateInstalled(
                template_slug=template.slug,
                project_slug=project_slug,
                project_id=str(project_id),
                installed_by=installed_by,
                macros_seeded=macros_seeded,
                kb_articles_seeded=kb_seeded,
                routing_rules_seeded=routing_seeded,
                warnings=tuple(warnings),
            )
        )
        return InstallResult(
            ok=True,
            project_id=str(project_id),
            macros_seeded=macros_seeded,
            kb_articles_seeded=kb_seeded,
            routing_rules_seeded=routing_seeded,
            warnings=tuple(warnings),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "templates.install_failed",
            template_slug=template.slug,
            project_slug=project_slug,
            error=str(exc),
        )
        await bus.publish(
            ProjectTemplateFailed(
                template_slug=template.slug,
                project_slug=project_slug,
                attempted_by=installed_by,
                error=str(exc),
            )
        )
        return InstallResult(ok=False, detail=f"exception: {exc}")
