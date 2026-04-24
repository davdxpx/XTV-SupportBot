"""Incoming / outgoing message events."""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class MessageReceived(DomainEvent):
    """A user DM'd the bot or posted in a ticket topic."""

    message_id: int
    chat_id: int
    user_id: int
    ticket_id: str | None = None
    text: str | None = None
    has_media: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class MessageSent(DomainEvent):
    """The bot successfully sent a message (user or topic)."""

    message_id: int
    chat_id: int
    ticket_id: str | None = None
    via: str = "bot"  # bot | macro | ai_draft | bridge
