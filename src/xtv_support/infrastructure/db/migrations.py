from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from xtv_support.config.settings import settings
from xtv_support.core.logger import get_logger

log = get_logger("migrations")

SCHEMA_VERSION = 8


async def _safe_drop_index(coll, name: str) -> None:
    try:
        await coll.drop_index(name)
        log.info("db.index_dropped", coll=coll.name, name=name)
    except OperationFailure:
        pass
    except Exception as exc:  # noqa: BLE001
        log.debug("db.index_drop_failed", coll=coll.name, name=name, error=str(exc))


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all indexes. Idempotent.

    The unique index on ``tickets.topic_id`` must use a partial filter
    expression instead of ``sparse=True`` — ``sparse`` only skips missing
    fields, not fields that are explicitly ``null``. A ticket that failed
    topic creation has ``topic_id=None`` and without the partial filter
    the second such document would collide on the unique constraint.
    """
    # Drop legacy indexes that we recreate with different options below.
    await _safe_drop_index(db.tickets, "ux_topic_id")

    await db.tickets.create_index(
        [("topic_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"topic_id": {"$type": "number"}},
        name="ux_topic_id",
    )
    await db.tickets.create_index(
        [("user_id", ASCENDING), ("status", ASCENDING)], name="ix_user_status"
    )
    await db.tickets.create_index(
        [("status", ASCENDING), ("sla_deadline", ASCENDING)], name="ix_sla"
    )
    await db.tickets.create_index(
        [("status", ASCENDING), ("last_user_msg_at", ASCENDING)], name="ix_stale_user"
    )
    await db.tickets.create_index(
        [("status", ASCENDING), ("last_admin_msg_at", ASCENDING)], name="ix_stale_admin"
    )
    await db.tickets.create_index([("assignee_id", ASCENDING)], name="ix_assignee")
    await db.tickets.create_index([("tags", ASCENDING)], name="ix_tags")

    await db.users.create_index([("user_id", ASCENDING)], unique=True, name="ux_user_id")
    await db.users.create_index([("blocked", ASCENDING)], name="ix_blocked")

    await db.projects.create_index(
        [("active", ASCENDING), ("created_at", DESCENDING)], name="ix_active_created"
    )

    await db.contact_links.create_index([("uuid", ASCENDING)], unique=True, name="ux_uuid")

    await db.tags.create_index([("name", ASCENDING)], unique=True, name="ux_tag_name")

    await db.broadcasts.create_index(
        [("state", ASCENDING), ("started_at", DESCENDING)], name="ix_state_started"
    )

    retention_seconds = max(1, settings.AUDIT_RETENTION_DAYS) * 86400
    await db.audit_log.create_index(
        [("ts", DESCENDING)], name="ix_ts_ttl", expireAfterSeconds=retention_seconds
    )

    # --- Phase 5: RBAC + Teams ---------------------------------------
    await db.roles.create_index([("user_id", ASCENDING)], unique=True, name="ux_role_user")
    await db.roles.create_index([("role", ASCENDING)], name="ix_role")
    await db.roles.create_index([("team_ids", ASCENDING)], name="ix_role_teams")

    await db.teams.create_index([("_id", ASCENDING)], name="ix_team_id")
    await db.teams.create_index([("member_ids", ASCENDING)], name="ix_team_members")

    # --- Phase 6: Macros ---------------------------------------------
    # Name must be unique per scope (team_id). Using a unique compound
    # lets the same macro name exist as both a global and a per-team
    # macro if the operator really wants that.
    await db.macros.create_index(
        [("name", ASCENDING), ("team_id", ASCENDING)],
        unique=True,
        name="ux_macro_name_scope",
    )
    await db.macros.create_index([("team_id", ASCENDING)], name="ix_macro_team")
    await db.macros.create_index([("tags", ASCENDING)], name="ix_macro_tags")

    # --- Phase 6b: Knowledge Base ------------------------------------
    await db.kb_articles.create_index([("slug", ASCENDING)], unique=True, name="ux_kb_slug")
    await db.kb_articles.create_index([("lang", ASCENDING)], name="ix_kb_lang")
    await db.kb_articles.create_index([("tags", ASCENDING)], name="ix_kb_tags")
    await db.kb_articles.create_index([("project_ids", ASCENDING)], name="ix_kb_projects")
    # Full-text index — title weighs more than body or tags so a
    # ``?q=reset password`` query with a matching title beats a body
    # hit by default.
    try:
        await db.kb_articles.create_index(
            [("title", "text"), ("body", "text"), ("tags", "text")],
            weights={"title": 10, "body": 3, "tags": 5},
            default_language="english",
            name="fts_kb",
        )
    except OperationFailure as exc:
        log.warning("db.kb_fts_index_failed", error=str(exc))

    log.info("db.indexes_ensured")


async def backfill_defaults(db: AsyncIOMotorDatabase) -> None:
    """Add missing fields to pre-existing documents. Never modifies existing values."""
    defaults = {
        "tags": [],
        "priority": "normal",
        "assignee_id": None,
        "assigned_at": None,
        "assigned_by": None,
        "sla_deadline": None,
        "sla_warned": False,
        "topic_fallback": False,
        "header_msg_id": None,
        # Phase 4.1 — internal notes + schema version marker on the ticket
        # for future forward-migrations. Both are idempotent: $exists is
        # False only the first time a given document is touched.
        "internal_notes": [],
        "history_version": 1,
    }
    for field, default in defaults.items():
        await db.tickets.update_many({field: {"$exists": False}}, {"$set": {field: default}})

    await db.tickets.update_many(
        {"last_user_msg_at": {"$exists": False}},
        [{"$set": {"last_user_msg_at": "$created_at"}}],
    )
    await db.tickets.update_many(
        {"last_admin_msg_at": {"$exists": False}}, {"$set": {"last_admin_msg_at": None}}
    )

    user_defaults = {
        "blocked": False,
        "cooldown_until": None,
        "flood_score": 0,
        "lang": settings.DEFAULT_LANG,
        "notified_on_assign": False,
    }
    for field, default in user_defaults.items():
        await db.users.update_many({field: {"$exists": False}}, {"$set": {field: default}})

    # --- Phase 4.2: project-template marker on legacy projects -------
    # Every existing project gets ``template_slug: "legacy"`` so analytics
    # and the admin UI can distinguish projects created before the
    # template system existed. Idempotent: $exists gate runs once per doc.
    await db.projects.update_many(
        {"template_slug": {"$exists": False}},
        {"$set": {"template_slug": "legacy"}},
    )

    # --- Seed RBAC from ADMIN_IDS (Phase 5) --------------------------
    # Every legacy admin is bootstrapped as Role.ADMIN unless a roles/
    # document for them already exists (respects manual overrides).
    from xtv_support.utils.time import utcnow as _utcnow

    for admin_id in settings.ADMIN_IDS:
        await db.roles.update_one(
            {"user_id": admin_id},
            {
                "$setOnInsert": {
                    "user_id": admin_id,
                    "role": "admin",
                    "team_ids": [],
                    "granted_by": None,
                    "granted_at": _utcnow(),
                }
            },
            upsert=True,
        )

    await db.configs.update_one(
        {"_id": "schema"},
        {"$set": {"version": SCHEMA_VERSION}},
        upsert=True,
    )
    log.info("db.backfill_defaults_done", version=SCHEMA_VERSION)


async def run(db: AsyncIOMotorDatabase) -> None:
    """Full migration entrypoint called at bootstrap."""
    await ensure_indexes(db)
    await backfill_defaults(db)


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
