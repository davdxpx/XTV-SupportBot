"""AI summariser plugin — records a structured summary on ticket close."""
from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import TicketClosed
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.plugins.base import EventSubscription, Plugin as _Base
from xtv_support.services.ai import summary as ai_summary

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.ai_summary")


class Plugin(_Base):
    name = "ai_summary"
    version = "0.1.0"
    feature_flag = "AI_SUMMARY"
    description = "Summarise a ticket into Problem / Resolution / Tags on close."

    def __init__(self) -> None:
        self._client: AIClient | None = None
        self._db = None

    async def on_startup(self, container: "Container") -> None:
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
        async def on_closed(event: TicketClosed) -> None:
            if self._client is None or not self._client.enabled:
                return
            if self._db is None:
                return

            # Lazy — keeps plugin discovery bson-free.
            from xtv_support.infrastructure.db import tickets as tickets_repo

            ticket = await tickets_repo.get(self._db, event.ticket_id)
            if not ticket:
                return
            conversation = _flatten_history(ticket.get("history") or [])
            if not conversation.strip():
                return

            result = await ai_summary.summarise(
                self._client,
                conversation_text=conversation,
                ticket_id=event.ticket_id,
            )
            if not result.ok:
                return

            try:
                from bson import ObjectId

                await self._db.tickets.update_one(
                    {"_id": ObjectId(event.ticket_id)},
                    {
                        "$set": {
                            "ai_summary": {
                                "problem": result.problem,
                                "resolution": result.resolution,
                                "tags": list(result.tags),
                            }
                        }
                    },
                )
            except Exception as exc:  # noqa: BLE001
                _log.debug(
                    "ai_summary.persist_failed",
                    ticket_id=event.ticket_id,
                    error=str(exc),
                )

        return [EventSubscription(event_type=TicketClosed, handler=on_closed)]


def _flatten_history(history: list[dict]) -> str:
    lines: list[str] = []
    for entry in history:
        sender = (entry.get("sender") or "user").capitalize()
        text = entry.get("text") or ""
        if text:
            lines.append(f"{sender}: {text}")
    return "\n".join(lines)
