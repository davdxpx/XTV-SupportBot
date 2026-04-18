from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import RPCError

from app.config import settings
from app.core.logger import get_logger
from app.db import tickets as tickets_repo
from app.services import topic_service
from app.utils.text import user_mention
from app.utils.time import utcnow

if TYPE_CHECKING:  # pragma: no cover
    from app.services.cooldown_service import CooldownService

log = get_logger("sla")


class SlaService:
    """Low-footprint SLA tracker.

    There is no in-memory schedule; the sla_task polls Mongo instead. This
    avoids races when the bot restarts. The service exposes helpers used by
    the handlers (cancel/reschedule) and the periodic task.
    """

    def __init__(self, client: Client, db: AsyncIOMotorDatabase):
        self._client = client
        self._db = db

    async def schedule(self, ticket_id, *, minutes: int | None = None) -> None:
        delta = timedelta(minutes=minutes or settings.SLA_WARN_MINUTES)
        await tickets_repo.set_sla(
            self._db, ticket_id, deadline=utcnow() + delta, warned=False
        )

    async def cancel(self, ticket_id) -> None:
        await tickets_repo.set_sla(self._db, ticket_id, deadline=None, warned=True)

    async def fire_once(self) -> int:
        """Run a single sweep. Returns the number of tickets that were warned."""
        breached = await tickets_repo.find_sla_breached(self._db)
        count = 0
        for ticket in breached:
            try:
                await self._warn(ticket)
                count += 1
            except Exception as exc:  # noqa: BLE001 - logged
                log.warning(
                    "sla.warn_failed",
                    ticket=str(ticket["_id"]),
                    error=str(exc),
                )
        return count

    async def _warn(self, ticket: dict[str, Any]) -> None:
        tid = ticket["_id"]
        await tickets_repo.set_sla(
            self._db, tid, deadline=ticket.get("sla_deadline"), warned=True
        )
        text = self._format_alert(ticket)
        topic_id = ticket.get("topic_id")
        try:
            await self._client.send_message(
                settings.ADMIN_CHANNEL_ID,
                text,
                parse_mode=ParseMode.HTML,
                message_thread_id=topic_id,
            )
        except RPCError as exc:
            log.warning("sla.alert_failed", ticket=str(tid), error=str(exc))
            return

        # Also rerender the header card so its bar flips to breached.
        project = None
        if ticket.get("project_id"):
            from app.db import projects as projects_repo

            project = await projects_repo.get(self._db, ticket["project_id"])
        try:
            await topic_service.rerender_header(
                self._client,
                self._db,
                ticket=ticket,
                project=project,
                user_name=str(ticket.get("user_id")),
                username=None,
                assignee_name=None,
            )
        except RPCError:
            pass

    @staticmethod
    def _format_alert(ticket: dict[str, Any]) -> str:
        short = str(ticket["_id"])[-6:]
        assignee = ticket.get("assignee_id")
        mention = user_mention(assignee, f"Admin {assignee}") if assignee else "team"
        return (
            f"<blockquote>SLA warning \u2022 Ticket #{short}\n\n"
            f"Attention {mention}: the user is waiting beyond the SLA window.\n"
            f"Please reply in this topic.</blockquote>"
        )

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
