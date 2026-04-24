"""AI smart-routing plugin.

Subscribes to :class:`TicketCreated`, reads the first user message,
suggests a team, and stores the suggestion under
``tickets.ai_suggested_team`` so the admin can review / confirm.
Never auto-reassigns.
"""

from xtv_support.plugins.builtin.ai_routing.plugin import Plugin

__all__ = ["Plugin"]
