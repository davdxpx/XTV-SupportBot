"""Email-ingestion plugin skeleton.

The plugin registers itself and its feature flag so operators can
toggle it via env; the actual IMAP poller + SMTP outbox are deferred
to v0.10. Toggling ``FEATURE_EMAIL_INGRESS=true`` today logs a
"scheduled" hint so operators don't expect an inbox sync yet.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from xtv_support.core.logger import get_logger
from xtv_support.plugins.base import Plugin as _Base

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.email_ingress")


class Plugin(_Base):
    name = "email_ingress"
    version = "0.1.0"
    feature_flag = "EMAIL_INGRESS"
    description = "IMAP-polled email -> ticket bridge (scaffolding, full impl in v0.10)."

    async def on_startup(self, container: "Container") -> None:
        _log.info("email_ingress.scaffolding_only")
