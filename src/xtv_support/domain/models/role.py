"""Role-assignment domain model.

A :class:`RoleAssignment` binds a :class:`Role` to a Telegram user id
and, optionally, to one or more teams (``team_ids``). The RBAC
middleware picks the *highest* role across all assignments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from xtv_support.domain.enums import Role


@dataclass(frozen=True, slots=True, kw_only=True)
class RoleAssignment:
    user_id: int
    role: Role
    team_ids: tuple[str, ...] = ()
    granted_by: int | None = None
    granted_at: datetime | None = None

    def belongs_to_team(self, team_id: str) -> bool:
        return team_id in self.team_ids
