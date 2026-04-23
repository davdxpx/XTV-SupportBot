"""Queue-routing engine.

Picks which team should own a newly-created ticket based on declarative
rules attached to each :class:`~xtv_support.domain.models.team.Team`.

Rules
-----
Each team carries a list of :class:`QueueRule` s. A rule is a match
dict + a weight::

    QueueRule(match={"tag": "billing"}, weight=200)
    QueueRule(match={"project_type": "feedback"}, weight=50)
    QueueRule(match={"priority": "urgent"}, weight=300)

Match keys (all optional — empty match wins by default on a catch-all):

* ``tag`` — any element of ``ticket.tags`` equals the value
* ``project_id`` — ticket's project equals the value
* ``project_type`` — ticket's project type (support / feedback / contact)
* ``priority`` — ticket's priority label

All provided keys must match for the rule to fire (AND across keys,
OR across rules / teams).

Selection
---------
* For each team, evaluate every rule. The team's score is the highest
  weight among matching rules (``0`` if no rule matched).
* The winning team is the one with the highest score. Ties broken by
  the team's order in the input list (stable sort).
* A team score of ``0`` means no rule matched — the team is skipped
  unless it is the only one with an empty-match (catch-all) rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from xtv_support.core.logger import get_logger
from xtv_support.domain.models.team import QueueRule, Team

log = get_logger("routing")


@dataclass(frozen=True, slots=True)
class RouteResult:
    """Outcome of a :func:`route_ticket` evaluation."""

    team: Team | None
    score: int
    matched_rules: tuple[str, ...]   # flat ``"key=value"`` strings for audit


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def route_ticket(ticket: Mapping[str, object], teams: Iterable[Team]) -> RouteResult:
    """Return the best-matching team for ``ticket`` (or ``None``).

    ``ticket`` is a mapping-like — we read ``tags``, ``project_id``,
    ``project_type``, ``priority`` off it. Accepting a dict (instead of
    a full model) means this function works equally well for raw Mongo
    docs and parsed dataclasses.
    """
    best: tuple[int, int, Team, tuple[str, ...]] | None = None  # (score, -idx, team, matches)
    for idx, team in enumerate(teams):
        score, matches = _score_team(ticket, team)
        if score <= 0:
            continue
        key = (score, -idx)
        if best is None or key > (best[0], best[1]):
            best = (score, -idx, team, matches)

    if best is None:
        log.debug("routing.no_match", ticket_id=ticket.get("_id"))
        return RouteResult(team=None, score=0, matched_rules=())

    _, _, team, matches = best
    log.info(
        "routing.matched",
        ticket_id=ticket.get("_id"),
        team=team.id,
        score=best[0],
        rules=matches,
    )
    return RouteResult(team=team, score=best[0], matched_rules=matches)


# ----------------------------------------------------------------------
# Internals — scoring
# ----------------------------------------------------------------------
def _score_team(
    ticket: Mapping[str, object], team: Team
) -> tuple[int, tuple[str, ...]]:
    best_score = 0
    matches: list[str] = []
    for rule in team.queue_rules:
        if _rule_matches(ticket, rule):
            if rule.weight > best_score:
                best_score = rule.weight
            matches.append(_rule_signature(rule))
    return best_score, tuple(matches)


def _rule_matches(ticket: Mapping[str, object], rule: QueueRule) -> bool:
    """AND across match keys. Empty match dict is treated as catch-all."""
    if not rule.match:
        return True
    for key, expected in rule.match.items():
        if key == "tag":
            tags = ticket.get("tags") or ()
            if isinstance(tags, str):
                tags = (tags,)
            if expected not in tags:
                return False
        elif key == "project_id":
            if str(ticket.get("project_id")) != str(expected):
                return False
        elif key == "project_type":
            if ticket.get("project_type") != expected:
                return False
        elif key == "priority":
            if ticket.get("priority") != expected:
                return False
        else:
            # Unknown key — fail-closed. Makes typos visible fast.
            return False
    return True


def _rule_signature(rule: QueueRule) -> str:
    """Stable string representation for audit logs."""
    if not rule.match:
        return f"catch-all @ w={rule.weight}"
    parts = ",".join(f"{k}={v}" for k, v in sorted(rule.match.items()))
    return f"{parts} @ w={rule.weight}"
