"""Start-captcha plugin — a light arithmetic gate before /start flows.

Registers only a CommandSpec for now; the actual pyrofork handler is
wired in alongside the other user flows once the plugin lifts its
shared-secret config out of env into settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.plugins.base import CommandSpec
from xtv_support.plugins.base import Plugin as _Base

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.start_captcha")


class Plugin(_Base):
    name = "start_captcha"
    version = "0.1.0"
    feature_flag = "START_CAPTCHA"
    description = "Require new users to solve a tiny captcha before /start."

    async def on_startup(self, container: Container) -> None:
        _log.info("start_captcha.startup")

    def register_commands(self) -> list[CommandSpec]:
        return [
            CommandSpec(
                name="captcha",
                scope="user",
                summary="Re-issue the start captcha (debugging).",
                feature_flag="START_CAPTCHA",
            )
        ]
