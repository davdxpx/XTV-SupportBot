"""Weekly analytics-digest plugin.

Schedules a weekly job that renders the last 7 days of rollups into
a forum-topic post. Uses the existing :class:`TaskManager` from
Phase 3 — the plugin only registers the loop on startup.

The actual posting relies on ``settings.ERROR_LOG_TOPIC_ID`` by
default (the same place tracebacks go); operators can override by
setting ``DIGEST_TOPIC_ID`` in the env if they want digests in a
different thread.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.plugins.base import Plugin as _Base
from xtv_support.services.analytics.digest import render

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.analytics_digest")

WEEK_SECONDS = 7 * 24 * 3600


class Plugin(_Base):
    name = "analytics_digest"
    version = "0.1.0"
    feature_flag = "ANALYTICS_DIGEST"
    description = "Weekly analytics summary posted to the admin topic."

    def __init__(self) -> None:
        self._container = None

    async def on_startup(self, container: Container) -> None:
        self._container = container
        tm = container.try_resolve(_task_manager_type())
        if tm is None:
            _log.warning("analytics_digest.no_task_manager")
            return
        tm.run_loop(self._tick, name="analytics_digest", interval=WEEK_SECONDS)

    async def _tick(self) -> None:
        if self._container is None:
            return
        db = self._container.try_resolve(_motor_db_type())
        client = self._container.try_resolve(_telegram_client_type())
        if db is None or client is None:
            _log.debug("analytics_digest.skipped missing_dep")
            return

        end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=7)
        rollups = [
            doc
            async for doc in db.analytics_daily.find(
                {"day": {"$gte": start.date().isoformat(), "$lt": end.date().isoformat()}}
            )
        ]
        payload = render(rollups, for_range="last 7 days")

        topic_id = os.environ.get("DIGEST_TOPIC_ID") or os.environ.get("ERROR_LOG_TOPIC_ID")
        admin_channel = os.environ.get("ADMIN_CHANNEL_ID")
        if not admin_channel:
            _log.debug("analytics_digest.no_admin_channel")
            return
        try:
            await client.send_message(
                chat_id=int(admin_channel),
                text=payload.full_html,
                message_thread_id=int(topic_id) if topic_id else None,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("analytics_digest.send_failed", error=str(exc))


# ----------------------------------------------------------------------
# Late-bound container lookups — keeps the plugin importable when motor
# / pyrofork are missing in trimmed CI images.
# ----------------------------------------------------------------------
def _task_manager_type():
    try:
        from xtv_support.tasks.scheduler import TaskManager

        return TaskManager
    except Exception:  # noqa: BLE001
        return type("TaskManager", (), {})


def _motor_db_type():
    try:
        from motor.motor_asyncio import AsyncIOMotorDatabase

        return AsyncIOMotorDatabase
    except Exception:  # noqa: BLE001
        return type("AsyncIOMotorDatabase", (), {})


def _telegram_client_type():
    try:
        from pyrogram import Client

        return Client
    except Exception:  # noqa: BLE001
        return type("Client", (), {})
