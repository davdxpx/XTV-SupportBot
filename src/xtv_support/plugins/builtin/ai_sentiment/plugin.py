"""AI sentiment plugin — labels incoming user messages."""
from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import MessageReceived
from xtv_support.infrastructure.ai.client import AIClient, AIConfig
from xtv_support.plugins.base import EventSubscription, Plugin as _Base
from xtv_support.services.ai import sentiment

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.ai_sentiment")


class Plugin(_Base):
    name = "ai_sentiment"
    version = "0.1.0"
    feature_flag = "AI_SENTIMENT"
    description = "Tag incoming user messages with a sentiment label."

    def __init__(self) -> None:
        self._client: AIClient | None = None
        self._db = None

    async def on_startup(self, container: "Container") -> None:
        self._client = _resolve_ai_client(container)
        db = container.try_resolve(_motor_type()) if _motor_type() else None
        self._db = db

    def subscribe_events(self) -> list[EventSubscription]:
        async def on_message(event: MessageReceived) -> None:
            if self._client is None or not self._client.enabled:
                return
            if not event.text or event.ticket_id is None:
                return
            result = await sentiment.classify(
                self._client,
                user_text=event.text,
                user_id=event.user_id,
                ticket_id=event.ticket_id,
            )
            if not result.confident:
                return
            # Persist the label on the ticket so the header card and
            # admin views can render it. Failures are non-fatal.
            if self._db is not None:
                try:
                    from bson import ObjectId

                    await self._db.tickets.update_one(
                        {"_id": ObjectId(event.ticket_id)},
                        {"$set": {"sentiment": result.sentiment.value}},
                    )
                except Exception as exc:  # noqa: BLE001
                    _log.debug(
                        "ai_sentiment.persist_failed",
                        ticket_id=event.ticket_id,
                        error=str(exc),
                    )

        return [EventSubscription(event_type=MessageReceived, handler=on_message)]


# ----------------------------------------------------------------------
# Helpers shared by every AI plugin — resolve the client + db from the
# container, tolerating the case where the ai extra isn't installed.
# ----------------------------------------------------------------------
def _resolve_ai_client(container) -> AIClient | None:
    try:
        return container.try_resolve(AIClient)
    except Exception:  # noqa: BLE001
        return None


def _motor_type():
    """Return ``AsyncIOMotorDatabase`` or None when motor isn't installed."""
    try:
        from motor.motor_asyncio import AsyncIOMotorDatabase

        return AsyncIOMotorDatabase
    except Exception:  # noqa: BLE001
        return None
