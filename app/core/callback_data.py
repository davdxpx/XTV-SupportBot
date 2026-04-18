from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from app.constants import CallbackPrefix

SEP = "|"


@dataclass(frozen=True)
class CbBase:
    """Typed callback_data. Subclasses declare prefix and fields."""

    prefix: ClassVar[str] = ""

    def pack(self) -> str:
        raise NotImplementedError

    @classmethod
    def unpack(cls, data: str) -> "CbBase":
        raise NotImplementedError


@dataclass(frozen=True)
class CbSimple(CbBase):
    """Callback with no extra payload."""

    prefix: ClassVar[str] = ""

    def pack(self) -> str:
        return self.prefix

    @classmethod
    def unpack(cls, data: str) -> "CbSimple":
        return cls()


@dataclass(frozen=True)
class CbProject(CbBase):
    prefix: ClassVar[str] = CallbackPrefix.ADMIN_PROJECT_VIEW
    project_id: str = ""

    def pack(self) -> str:
        return f"{self.prefix}{SEP}{self.project_id}"

    @classmethod
    def unpack(cls, data: str) -> "CbProject":
        _, pid = data.split(SEP, 1)
        return cls(project_id=pid)


@dataclass(frozen=True)
class CbProjectAction(CbBase):
    """Generic (prefix, project_id) pair for delete/tickets/etc."""

    prefix: ClassVar[str] = ""
    project_id: str = ""

    @classmethod
    def for_prefix(cls, prefix: str, project_id: str) -> str:
        return f"{prefix}{SEP}{project_id}"


@dataclass(frozen=True)
class CbTicket(CbBase):
    """Ticket-scoped callback. Subclass sets prefix."""

    prefix: ClassVar[str] = ""
    ticket_id: str = ""

    def pack(self) -> str:
        return f"{self.prefix}{SEP}{self.ticket_id}"

    @classmethod
    def unpack(cls, data: str) -> "CbTicket":
        _, tid = data.split(SEP, 1)
        return cls(ticket_id=tid)


@dataclass(frozen=True)
class CbAssignPick(CbBase):
    prefix: ClassVar[str] = CallbackPrefix.TICKET_ASSIGN_PICK
    ticket_id: str = ""
    admin_id: int = 0

    def pack(self) -> str:
        return f"{self.prefix}{SEP}{self.ticket_id}{SEP}{self.admin_id}"

    @classmethod
    def unpack(cls, data: str) -> "CbAssignPick":
        _, tid, aid = data.split(SEP, 2)
        return cls(ticket_id=tid, admin_id=int(aid))


@dataclass(frozen=True)
class CbTagToggle(CbBase):
    prefix: ClassVar[str] = CallbackPrefix.TICKET_TAG_TOGGLE
    ticket_id: str = ""
    tag: str = ""

    def pack(self) -> str:
        return f"{self.prefix}{SEP}{self.ticket_id}{SEP}{self.tag}"

    @classmethod
    def unpack(cls, data: str) -> "CbTagToggle":
        _, tid, tag = data.split(SEP, 2)
        return cls(ticket_id=tid, tag=tag)


@dataclass(frozen=True)
class CbPriorityPick(CbBase):
    prefix: ClassVar[str] = CallbackPrefix.TICKET_PRIORITY_PICK
    ticket_id: str = ""
    priority: str = "normal"

    def pack(self) -> str:
        return f"{self.prefix}{SEP}{self.ticket_id}{SEP}{self.priority}"

    @classmethod
    def unpack(cls, data: str) -> "CbPriorityPick":
        _, tid, prio = data.split(SEP, 2)
        return cls(ticket_id=tid, priority=prio)


@dataclass(frozen=True)
class CbRate(CbBase):
    prefix: ClassVar[str] = CallbackPrefix.USER_RATE
    project_id: str = ""
    score: int = 0

    def pack(self) -> str:
        return f"{self.prefix}{SEP}{self.project_id}{SEP}{self.score}"

    @classmethod
    def unpack(cls, data: str) -> "CbRate":
        _, pid, score = data.split(SEP, 2)
        return cls(project_id=pid, score=int(score))


def starts_with(prefix: str) -> str:
    """Regex fragment that matches callbacks starting with the given prefix."""
    import re

    return rf"^{re.escape(prefix)}(?:\{SEP}|$)"
