"""Domain events for the in-process event bus.

Events are immutable, keyword-only dataclasses. Subscribers live in
services / plugins and attach via :meth:`xtv_support.core.events.EventBus.on`
or :meth:`~xtv_support.core.events.EventBus.subscribe`.
"""
from __future__ import annotations

from xtv_support.domain.events.base import DomainEvent
from xtv_support.domain.events.broadcasts import (
    BroadcastCancelled,
    BroadcastFinished,
    BroadcastPaused,
    BroadcastResumed,
    BroadcastStarted,
)
from xtv_support.domain.events.messaging import MessageReceived, MessageSent
from xtv_support.domain.events.plugins import PluginFailed, PluginLoaded, PluginUnloaded
from xtv_support.domain.events.projects import ProjectCreated, ProjectDeleted
from xtv_support.domain.events.sla import SlaBreached, SlaWarned
from xtv_support.domain.events.tickets import (
    TicketAssigned,
    TicketClosed,
    TicketCreated,
    TicketPriorityChanged,
    TicketReopened,
    TicketRoutedToTeam,
    TicketTagged,
)
from xtv_support.domain.events.users import (
    UserBlocked,
    UserLanguageChanged,
    UserRegistered,
    UserUnblocked,
)

__all__ = [
    "DomainEvent",
    # Tickets
    "TicketCreated",
    "TicketAssigned",
    "TicketTagged",
    "TicketPriorityChanged",
    "TicketClosed",
    "TicketReopened",
    "TicketRoutedToTeam",
    # SLA
    "SlaWarned",
    "SlaBreached",
    # Messaging
    "MessageReceived",
    "MessageSent",
    # Users
    "UserRegistered",
    "UserBlocked",
    "UserUnblocked",
    "UserLanguageChanged",
    # Broadcasts
    "BroadcastStarted",
    "BroadcastPaused",
    "BroadcastResumed",
    "BroadcastCancelled",
    "BroadcastFinished",
    # Projects
    "ProjectCreated",
    "ProjectDeleted",
    # Plugins
    "PluginLoaded",
    "PluginUnloaded",
    "PluginFailed",
]
