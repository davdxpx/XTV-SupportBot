"""Slack Block-Kit formatter.

Takes the same domain events as the Discord formatter and produces
Slack-compatible JSON. Colours are expressed as ``attachments[].color``
so the sidebar renders accordingly.
"""

from __future__ import annotations

from typing import Any

from xtv_support.domain.events import (
    DomainEvent,
    SlaBreached,
    TicketAssigned,
    TicketClosed,
    TicketCreated,
    TicketReopened,
)

_COLOUR_INFO = "#3498db"
_COLOUR_OK = "#2ecc71"
_COLOUR_WARN = "#f1c40f"
_COLOUR_DANGER = "#e74c3c"


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_payload(event: DomainEvent) -> dict[str, Any] | None:
    """Slack incoming-webhook JSON. ``None`` when the event isn't bridged."""
    if isinstance(event, TicketCreated):
        return {
            "attachments": [
                {
                    "color": _COLOUR_INFO,
                    "blocks": [
                        _section(f"*🎫 Ticket #{event.ticket_id}* opened"),
                        _section(f"*User:* {event.user_id}\n*Project:* {event.project_id or '—'}"),
                    ],
                }
            ]
        }
    if isinstance(event, TicketAssigned):
        assignee = event.assignee_id or "cleared"
        return {
            "attachments": [
                {
                    "color": _COLOUR_INFO,
                    "blocks": [
                        _section(f"*📌 Ticket #{event.ticket_id}* assigned to *{assignee}*"),
                    ],
                }
            ]
        }
    if isinstance(event, TicketClosed):
        return {
            "attachments": [
                {
                    "color": _COLOUR_OK,
                    "blocks": [
                        _section(
                            f"*✅ Ticket #{event.ticket_id}* closed (reason: `{event.reason}`)"
                        ),
                    ],
                }
            ]
        }
    if isinstance(event, TicketReopened):
        return {
            "attachments": [
                {
                    "color": _COLOUR_WARN,
                    "blocks": [_section(f"*🔓 Ticket #{event.ticket_id}* reopened")],
                }
            ]
        }
    if isinstance(event, SlaBreached):
        return {
            "attachments": [
                {
                    "color": _COLOUR_DANGER,
                    "blocks": [
                        _section(f"*🔥 SLA breach* — ticket #{event.ticket_id}"),
                        _section(
                            f"Waited *{event.age_seconds // 60}m* "
                            f"(limit {event.breach_after_seconds // 60}m)"
                        ),
                    ],
                }
            ]
        }
    return None
