"""High-level macro service.

Thin orchestration on top of :mod:`xtv_support.infrastructure.db.macros`
that adds two things:

* ``render(macro, **context)`` — template substitution with ``{name}``
  placeholders for caller-provided context (user name, ticket id, …).
  Missing placeholders never raise; the raw template is returned with
  an ``i18n``-style warning log so mistakes become visible.

* ``consume(db, bus, macro, ticket_id, actor_id)`` — increments
  ``usage_count`` and publishes :class:`MacroUsed`. Services call this
  exactly once per successful insertion into a ticket.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import MacroUsed
from xtv_support.domain.models.macro import Macro
from xtv_support.infrastructure.db import macros as macros_repo

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from xtv_support.core.events import EventBus

_log = get_logger("macros")


def render(macro: Macro, **context: Any) -> str:
    """Expand ``{placeholder}`` tokens in the macro body.

    Missing placeholders are non-fatal — the raw template is returned
    so an agent that forgets to pass ``user_name`` still sees the
    canned text.
    """
    try:
        return macro.body.format(**context)
    except (KeyError, IndexError) as exc:
        _log.warning(
            "macro.placeholder_missing",
            macro=macro.name,
            error=str(exc),
            provided=list(context.keys()),
        )
        return macro.body


async def consume(
    db: AsyncIOMotorDatabase,
    bus: EventBus,
    *,
    macro: Macro,
    ticket_id: str,
    actor_id: int,
) -> None:
    """Book-keeping after a macro was successfully inserted somewhere."""
    try:
        await macros_repo.increment_usage(db, macro.id)
    except Exception as exc:  # noqa: BLE001 — never let DB errors break UX
        _log.warning("macro.usage_bump_failed", macro=macro.name, error=str(exc))

    await bus.publish(
        MacroUsed(
            macro_id=macro.id,
            macro_name=macro.name,
            ticket_id=ticket_id,
            actor_id=actor_id,
            team_id=macro.team_id,
        )
    )


async def find_for_team(
    db: AsyncIOMotorDatabase,
    name: str,
    *,
    team_id: str | None,
) -> Macro | None:
    """Team-first lookup with global fallback — wraps the repo helper."""
    return await macros_repo.get_by_name(db, name, team_id=team_id)
