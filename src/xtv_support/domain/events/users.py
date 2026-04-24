"""User-lifecycle events."""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: int
    language_code: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserBlocked(DomainEvent):
    user_id: int
    actor_id: int
    reason: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserUnblocked(DomainEvent):
    user_id: int
    actor_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UserLanguageChanged(DomainEvent):
    user_id: int
    new_language: str
