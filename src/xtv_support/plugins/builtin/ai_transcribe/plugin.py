"""Voice/image transcription plugin.

Subscribes to :class:`MessageReceived` with ``has_media=True`` and, if
the media carries a retrievable URL, runs image-OCR (or voice STT).
The actual Telegram-file download happens in the pyrofork handler
stack — this plugin only orchestrates once the infra layer has a
fetchable URL. For the initial v0.9 release only the image code path
is wired; voice transcription hooks in later once the media service
has a reliable temp-URL pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import MessageReceived
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.plugins.base import EventSubscription
from xtv_support.plugins.base import Plugin as _Base
from xtv_support.services.ai import transcribe as ai_transcribe

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.ai_transcribe")


class Plugin(_Base):
    name = "ai_transcribe"
    version = "0.1.0"
    feature_flag = "AI_TRANSCRIBE"
    description = "Transcribe voice notes / OCR images so agents can read them at a glance."

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
        async def on_message(event: MessageReceived) -> None:
            if self._client is None or not self._client.enabled:
                return
            if not event.has_media or event.ticket_id is None:
                return
            # The MessageReceived event carries the text (if any) and a
            # has_media flag. The actual media URL is attached by the
            # Telegram infra layer under ``ticket.last_media_url`` so
            # this plugin looks it up rather than pulling bytes itself.
            if self._db is None:
                return
            from bson import ObjectId

            ticket = await self._db.tickets.find_one(
                {"_id": ObjectId(event.ticket_id)},
                projection={"last_media_url": 1, "last_media_kind": 1},
            )
            url = (ticket or {}).get("last_media_url")
            kind = (ticket or {}).get("last_media_kind") or "image"
            if not url:
                return

            if kind == "image":
                result = await ai_transcribe.transcribe_image(
                    self._client,
                    image_url=url,
                    user_id=event.user_id,
                    ticket_id=event.ticket_id,
                )
            else:
                # Voice path requires raw bytes — skipped in v0.9.
                return

            if not result.ok:
                return

            try:
                await self._db.tickets.update_one(
                    {"_id": ObjectId(event.ticket_id)},
                    {
                        "$push": {
                            "transcriptions": {
                                "message_id": event.message_id,
                                "kind": result.kind,
                                "text": result.text,
                            }
                        }
                    },
                )
            except Exception as exc:  # noqa: BLE001
                _log.debug(
                    "ai_transcribe.persist_failed",
                    ticket_id=event.ticket_id,
                    error=str(exc),
                )

        return [EventSubscription(event_type=MessageReceived, handler=on_message)]
