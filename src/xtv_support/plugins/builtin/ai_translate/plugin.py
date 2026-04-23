"""Auto-translation plugin.

Subscribes to :class:`MessageReceived` and, when the message came from
a language the bot's default locale differs from, runs a translation
and stashes it under ``tickets.translations[<lang>]`` so the topic
renderer can show both the original and the English version side by
side.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import MessageReceived
from xtv_support.infrastructure.ai.client import AIClient
from xtv_support.plugins.base import EventSubscription, Plugin as _Base
from xtv_support.services.ai import translate as ai_translate

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.ai_translate")


class Plugin(_Base):
    name = "ai_translate"
    version = "0.1.0"
    feature_flag = "AI_TRANSLATE"
    description = "Translate incoming non-default-locale messages for agents."

    def __init__(self) -> None:
        self._client: AIClient | None = None
        self._db = None
        self._default_lang = "en"

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
        # settings are available on the handler context, but plugins
        # only hold the container — fetch the default lang via the
        # FeatureFlags / Settings instances registered as singletons.
        try:
            from xtv_support.config.settings import Settings

            settings = container.try_resolve(Settings)
            if settings is not None:
                self._default_lang = settings.DEFAULT_LANG
        except Exception:  # noqa: BLE001
            pass

    def subscribe_events(self) -> list[EventSubscription]:
        async def on_message(event: MessageReceived) -> None:
            if self._client is None or not self._client.enabled:
                return
            if not event.text or event.ticket_id is None:
                return

            result = await ai_translate.translate(
                self._client,
                source_text=event.text,
                target_lang=self._default_lang,
                user_id=event.user_id,
                ticket_id=event.ticket_id,
            )
            if not result.ok or result.same_as_source:
                return

            if self._db is None:
                return
            try:
                from bson import ObjectId

                await self._db.tickets.update_one(
                    {"_id": ObjectId(event.ticket_id)},
                    {
                        "$push": {
                            "translations": {
                                "message_id": event.message_id,
                                "lang": self._default_lang,
                                "text": result.translated,
                            }
                        }
                    },
                )
            except Exception as exc:  # noqa: BLE001
                _log.debug(
                    "ai_translate.persist_failed",
                    ticket_id=event.ticket_id,
                    error=str(exc),
                )

        return [EventSubscription(event_type=MessageReceived, handler=on_message)]
