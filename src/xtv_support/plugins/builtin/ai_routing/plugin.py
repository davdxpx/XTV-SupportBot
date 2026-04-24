"""AI routing suggestion plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import TicketCreated
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.infrastructure.db import teams as teams_repo
from xtv_support.plugins.base import EventSubscription
from xtv_support.plugins.base import Plugin as _Base
from xtv_support.services.ai import routing as ai_routing

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.ai_routing")


class Plugin(_Base):
    name = "ai_routing"
    version = "0.1.0"
    feature_flag = "AI_ROUTING"
    description = "Suggest a team for new tickets based on the first message."

    def __init__(self) -> None:
        self._client: AIClient | None = None
        self._db = None

    async def on_startup(self, container: Container) -> None:
        try:
            self._client = container.try_resolve(AIClient)
        except Exception:  # noqa: BLE001
            self._client = None
        try:
            from motor.motor_asyncio import AsyncIOMotorDatabase

            self._db = container.try_resolve(AsyncIOMotorDatabase)
        except Exception:  # noqa: BLE001
            self._db = None

    def subscribe_events(self) -> list[EventSubscription]:
        async def on_created(event: TicketCreated) -> None:
            if self._client is None or not self._client.enabled:
                return
            if self._db is None:
                return

            # Lazy — keeps plugin discovery bson-free.
            from xtv_support.infrastructure.db import tickets as tickets_repo

            ticket = await tickets_repo.get(self._db, event.ticket_id)
            first_message = (ticket or {}).get("message") or ""
            if not first_message:
                return

            teams = await teams_repo.list_all(self._db)
            if not teams:
                return
            team_tuples = [(t.id, t.name) for t in teams]

            suggestion = await ai_routing.suggest(
                self._client,
                user_text=first_message,
                teams=team_tuples,
                user_id=event.user_id,
                ticket_id=event.ticket_id,
            )
            if not suggestion.confident:
                return

            try:
                from bson import ObjectId

                await self._db.tickets.update_one(
                    {"_id": ObjectId(event.ticket_id)},
                    {"$set": {"ai_suggested_team": suggestion.team_id}},
                )
            except Exception as exc:  # noqa: BLE001
                _log.debug(
                    "ai_routing.persist_failed",
                    ticket_id=event.ticket_id,
                    error=str(exc),
                )

        return [EventSubscription(event_type=TicketCreated, handler=on_created)]
