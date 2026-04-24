"""KB-drafter plugin — /ai kb-draft to scaffold a /kb add payload."""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.plugins.base import CommandSpec
from xtv_support.plugins.base import Plugin as _Base

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.ai_kb_drafter")


class Plugin(_Base):
    name = "ai_kb_drafter"
    version = "0.1.0"
    feature_flag = "AI_KB_DRAFTER"
    description = (
        "Adds /ai kb-draft inside topics to auto-generate a KB article "
        "from the current ticket's conversation."
    )

    async def on_startup(self, container: Container) -> None:
        _log.info("ai_kb_drafter.startup")

    def register_commands(self) -> list[CommandSpec]:
        return [
            CommandSpec(
                name="ai kb-draft",
                scope="topic",
                summary="Draft a KB article from this ticket's conversation.",
                feature_flag="AI_KB_DRAFTER",
            )
        ]
