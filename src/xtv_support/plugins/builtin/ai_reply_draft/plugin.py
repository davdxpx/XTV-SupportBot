"""Agent-triggered reply-draft plugin.

Unlike the event-driven plugins above, this one registers a topic
command (``/draft``) that an agent runs from inside a ticket topic.
The command builds a conversation from the ticket history, asks the
AI for a draft, and posts the result as a reply in the topic (not to
the user — agents always review).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.plugins.base import CommandSpec, Plugin as _Base

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.ai_reply_draft")


class Plugin(_Base):
    name = "ai_reply_draft"
    version = "0.1.0"
    feature_flag = "AI_DRAFTS"
    description = (
        "Adds /draft inside ticket topics so agents can get a suggested reply."
    )

    async def on_startup(self, container: "Container") -> None:
        _log.info("ai_reply_draft.startup")

    def register_commands(self) -> list[CommandSpec]:
        return [
            CommandSpec(
                name="draft",
                scope="topic",
                summary="Suggest a reply the agent can edit and send.",
                feature_flag="AI_DRAFTS",
            )
        ]

    # The pyrofork handler itself lives in
    # ``xtv_support.handlers.topic.ai_draft`` and is registered via the
    # router alongside the other topic commands. Keeping the /draft
    # logic next to the other topic handlers keeps the import graph
    # simple (pyrofork decorators run at import time).
