"""Slack-bridge plugin — mirrors ticket events into a Slack channel.

Structure mirrors the Discord bridge: build the payload via
:mod:`xtv_support.services.bridges.slack` and POST via httpx when
installed. SLACK_WEBHOOK_URL is the only required env var.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import (
    SlaBreached,
    TicketAssigned,
    TicketClosed,
    TicketCreated,
    TicketReopened,
)
from xtv_support.plugins.base import EventSubscription
from xtv_support.plugins.base import Plugin as _Base
from xtv_support.services.bridges.slack import build_payload

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.core.container import Container

_log = get_logger("plugin.slack_bridge")


class Plugin(_Base):
    name = "slack_bridge"
    version = "0.1.0"
    feature_flag = "SLACK_BRIDGE"
    description = "Mirror ticket events into a Slack channel via incoming webhook."

    def __init__(self) -> None:
        self._webhook_url: str | None = None

    async def on_startup(self, container: Container) -> None:
        self._webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or None
        if not self._webhook_url:
            _log.warning("slack_bridge.no_url")

    def subscribe_events(self) -> list[EventSubscription]:
        async def fan_out(event) -> None:
            if not self._webhook_url:
                return
            payload = build_payload(event)
            if payload is None:
                return
            await _post(self._webhook_url, payload)

        return [
            EventSubscription(event_type=TicketCreated, handler=fan_out),
            EventSubscription(event_type=TicketAssigned, handler=fan_out),
            EventSubscription(event_type=TicketClosed, handler=fan_out),
            EventSubscription(event_type=TicketReopened, handler=fan_out),
            EventSubscription(event_type=SlaBreached, handler=fan_out),
        ]


async def _post(url: str, payload: dict[str, Any]) -> None:
    try:
        import httpx  # type: ignore[import-untyped]
    except ModuleNotFoundError:
        _log.debug("slack_bridge.httpx_missing")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                content=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code >= 400:
                _log.warning(
                    "slack_bridge.post_failed",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
    except Exception as exc:  # noqa: BLE001
        _log.warning("slack_bridge.post_error", error=str(exc))
