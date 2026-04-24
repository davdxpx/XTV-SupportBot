"""Domain enums — single source of truth for role / priority / status constants.

Today these values live as ``Literal[…]`` aliases in
:mod:`xtv_support.infrastructure.db.schemas` and as legacy strings in
handlers. Formalising them here gives the RBAC / teams / escalation
code a common type to import.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Role(StrEnum):
    """Permission levels. Compared by :attr:`rank` — higher wins."""

    USER = "user"
    VIEWER = "viewer"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    OWNER = "owner"

    @property
    def rank(self) -> int:
        return _ROLE_RANK[self]

    def can(self, required: Role) -> bool:
        """True iff this role is at least as privileged as ``required``."""
        return self.rank >= required.rank

    @classmethod
    def from_string(cls, raw: str | None, *, default: Role | None = None) -> Role:
        """Parse a string, falling back to ``default`` (or :attr:`USER`)."""
        if raw is None:
            return default or cls.USER
        try:
            return cls(raw.strip().lower())
        except ValueError:
            return default or cls.USER


_ROLE_RANK: dict[Role, int] = {
    Role.USER: 0,
    Role.VIEWER: 1,
    Role.AGENT: 2,
    Role.SUPERVISOR: 3,
    Role.ADMIN: 4,
    Role.OWNER: 5,
}


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def rank(self) -> int:
        return _PRIORITY_RANK[self]


_PRIORITY_RANK: dict[Priority, int] = {
    Priority.LOW: 0,
    Priority.NORMAL: 1,
    Priority.HIGH: 2,
    Priority.URGENT: 3,
}


class TicketStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    CLOSED = "closed"


class ProjectType(StrEnum):
    SUPPORT = "support"
    FEEDBACK = "feedback"
    CONTACT = "contact"


class TicketSentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
