"""Role-based access control — pure, reusable logic.

The pyrofork middleware in :mod:`xtv_support.middlewares.rbac_mw` does
nothing but read/write the :data:`current_role` ContextVar from this
module. Handlers call :func:`require` / :func:`decide` from here so
tests and non-Telegram code paths can exercise permission checks
without pulling pyrogram.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextvars import ContextVar
from typing import TYPE_CHECKING

from xtv_support.core.errors import AdminOnly
from xtv_support.core.logger import get_logger
from xtv_support.domain.enums import Role

if TYPE_CHECKING:  # pragma: no cover — type-only
    from motor.motor_asyncio import AsyncIOMotorDatabase

log = get_logger("rbac")

#: Per-update resolved role. Defaults to ``Role.USER`` so handlers that
#: accidentally bypass the middleware still get the *least* privileges.
current_role: ContextVar[Role] = ContextVar("current_role", default=Role.USER)


# ----------------------------------------------------------------------
# Pure decision logic
# ----------------------------------------------------------------------
def decide(actual: Role, required: Iterable[Role]) -> bool:
    """True iff ``actual`` is at least as privileged as *any* required role.

    Accepts either a single :class:`Role` or an iterable. Treat it as
    an OR: user satisfies the check if they match any entry. An empty
    iterable always allows.
    """
    required_list = list(required)
    if not required_list:
        return True
    threshold = min(r.rank for r in required_list)
    return actual.rank >= threshold


def current() -> Role:
    """Return the role resolved for the active update."""
    return current_role.get()


def require(*required: Role) -> None:
    """Raise :class:`AdminOnly` when the caller's role is insufficient."""
    actual = current()
    if not decide(actual, required):
        log.info(
            "rbac.denied",
            actual=str(actual),
            required=[str(r) for r in required],
        )
        raise AdminOnly()


# ----------------------------------------------------------------------
# DB-backed resolver
# ----------------------------------------------------------------------
async def resolve_role(
    db: AsyncIOMotorDatabase,
    user_id: int,
    *,
    legacy_admin_ids: Iterable[int] | None = None,
) -> Role:
    """Look up the user's role in ``roles``; fall back to ADMIN_IDS.

    Parameters
    ----------
    db:
        Motor database handle passed to the repo.
    user_id:
        Telegram user id.
    legacy_admin_ids:
        Override for the env-derived list. ``None`` (default) lazy-
        imports :data:`xtv_support.config.settings.settings` — the
        production code path. Tests pass an explicit iterable and
        skip the full pydantic Settings stack.

    Precedence:
    1. ``roles.find_one({user_id})``
    2. ``legacy_admin_ids`` -> :attr:`Role.ADMIN`
    3. :attr:`Role.USER`
    """
    # Lazy imports so importing this module doesn't pull motor or pydantic.
    from xtv_support.infrastructure.db import roles as roles_repo

    try:
        assignment = await roles_repo.get_role(db, user_id)
    except Exception as exc:  # noqa: BLE001 — DB errors must not crash dispatch
        log.warning("rbac.lookup_failed", user_id=user_id, error=str(exc))
        assignment = None
    if assignment is not None:
        return assignment.role

    if legacy_admin_ids is None:
        from xtv_support.config.settings import settings

        legacy_admin_ids = settings.ADMIN_IDS
    if user_id in legacy_admin_ids:
        return Role.ADMIN
    return Role.USER
