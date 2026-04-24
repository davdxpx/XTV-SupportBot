"""Discord embed formatter.

Consumes domain events and produces the JSON payload Discord's
``Incoming Webhook`` endpoint expects. Pure — the pyrofork plugin in
``plugins/builtin/discord_bridge`` handles the actual HTTP POST.
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

# Discord embed colours (decimal).
_COLOUR_INFO = 3_447_003  # #3498db
_COLOUR_OK = 3_066_993  # #2ecc71
_COLOUR_WARN = 15_844_367  # #f1c40f
_COLOUR_DANGER = 15_158_332  # #e74c3c


def embed_for(event: DomainEvent) -> dict[str, Any] | None:
    """Return a Discord ``embed`` dict for events we bridge, or None."""
    if isinstance(event, TicketCreated):
        return {
            "title": f"🎫 Ticket #{event.ticket_id}",
            "description": f"New ticket opened by <t:user:{event.user_id}>.",
            "color": _COLOUR_INFO,
            "fields": [
                {"name": "User", "value": str(event.user_id), "inline": True},
                {"name": "Project", "value": event.project_id or "—", "inline": True},
            ],
        }
    if isinstance(event, TicketAssigned):
        return {
            "title": f"📌 Ticket #{event.ticket_id} assigned",
            "color": _COLOUR_INFO,
            "fields": [
                {
                    "name": "Assignee",
                    "value": str(event.assignee_id) if event.assignee_id else "cleared",
                    "inline": True,
                },
                {"name": "By", "value": str(event.assigned_by), "inline": True},
            ],
        }
    if isinstance(event, TicketClosed):
        return {
            "title": f"✅ Ticket #{event.ticket_id} closed",
            "description": f"Reason: `{event.reason}`",
            "color": _COLOUR_OK,
            "fields": [
                {"name": "Closed by", "value": str(event.closed_by), "inline": True},
            ],
        }
    if isinstance(event, TicketReopened):
        return {
            "title": f"🔓 Ticket #{event.ticket_id} reopened",
            "color": _COLOUR_WARN,
            "fields": [
                {"name": "By", "value": str(event.reopened_by), "inline": True},
            ],
        }
    if isinstance(event, SlaBreached):
        return {
            "title": f"🔥 SLA breach — ticket #{event.ticket_id}",
            "description": (
                f"Waited {event.age_seconds // 60}m (limit {event.breach_after_seconds // 60}m)."
            ),
            "color": _COLOUR_DANGER,
        }
    return None


def build_payload(event: DomainEvent) -> dict[str, Any] | None:
    embed = embed_for(event)
    if embed is None:
        return None
    return {"embeds": [embed]}
