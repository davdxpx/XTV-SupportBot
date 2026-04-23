"""High-level routing dispatcher.

Glues :mod:`xtv_support.services.teams.routing` together with the DB
layer and the event bus so services that create tickets only need to
call a single coroutine::

    await assign_to_team(db, bus, ticket_doc)

That call:
1. Loads every registered team from the DB.
2. Runs the pure :func:`route_ticket` engine.
3. Persists ``ticket.team_id`` on the ticket document (if matched).
4. Publishes :class:`TicketRoutedToTeam` on the event bus so plugins
   and notifiers can react.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from xtv_support.core.logger import get_logger
from xtv_support.domain.events import TicketRoutedToTeam
from xtv_support.infrastructure.db import teams as teams_repo
from xtv_support.services.teams.routing import RouteResult, route_ticket

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from xtv_support.core.events import EventBus

log = get_logger("teams.dispatcher")


async def assign_to_team(
    db: "AsyncIOMotorDatabase",
    bus: "EventBus",
    ticket: Mapping[str, object],
    *,
    persist: bool = True,
) -> RouteResult:
    """Route ``ticket`` to a team and emit the event.

    Parameters
    ----------
    db, bus:
        Infrastructure handles.
    ticket:
        Mapping with at minimum ``_id``. The engine reads ``tags``,
        ``project_id``, ``project_type``, ``priority``.
    persist:
        When True (default) the owning team's id is written back to
        the ``tickets`` collection on match. Set to False for
        dry-runs / admin previews.
    """
    teams = await teams_repo.list_all(db)
    if not teams:
        log.debug("routing.no_teams_configured", ticket_id=ticket.get("_id"))
        return RouteResult(team=None, score=0, matched_rules=())

    result = route_ticket(ticket, teams)
    if result.team is None:
        return result

    if persist and ticket.get("_id") is not None:
        try:
            await db.tickets.update_one(
                {"_id": ticket["_id"]}, {"$set": {"team_id": result.team.id}}
            )
        except Exception as exc:  # noqa: BLE001 — don't let a Mongo blip eat the event
            log.warning(
                "routing.persist_failed",
                ticket_id=ticket.get("_id"),
                team=result.team.id,
                error=str(exc),
            )

    await bus.publish(
        TicketRoutedToTeam(
            ticket_id=str(ticket.get("_id")),
            team_id=result.team.id,
            reason="auto",
            matched_rules=result.matched_rules,
        )
    )
    return result
