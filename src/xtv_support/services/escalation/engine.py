"""Escalation engine.

Evaluates rules against a domain event + ticket context and returns
the list of actions to apply. Pure, unit-testable — the plugin that
hangs onto the event bus (phase 8c after CSAT is wired) calls this
with the ticket document and publishes the resulting actions.

Rule semantics
--------------
* ``when`` matches the **event**: ``sla_breached`` (SLA breach events),
  ``ticket_tagged`` (tag added), ``ticket_created``. Extra filters on
  ``tag`` / ``priority`` / ``project_id`` must all match.
* Multiple matching rules fire in declared order; callers dedupe
  actions on the same ticket.
* ``cooldown_s`` is enforced by the caller (keeps engine pure).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from xtv_support.domain.models.escalation import EscalationRule


@dataclass(frozen=True, slots=True)
class EscalationOutcome:
    """A matched rule + the actions it wants to apply."""

    rule: EscalationRule


def evaluate(
    event: str,
    ticket: Mapping[str, object],
    rules: Iterable[EscalationRule],
    *,
    ticket_team_id: str | None = None,
    tag_added: str | None = None,
) -> list[EscalationOutcome]:
    """Return every matching, enabled rule in declared order.

    Parameters
    ----------
    event:
        One of ``sla_breached`` / ``ticket_tagged`` / ``ticket_created``.
    ticket:
        Mapping with ``priority``, ``tags``, ``project_id`` — raw
        ticket doc works.
    rules:
        Rules to evaluate. Rules scoped to a specific team match only
        when ``ticket_team_id`` equals ``rule.team_id`` (``None`` team
        == global).
    tag_added:
        The tag that triggered a ``ticket_tagged`` event; ignored for
        other events.
    """
    out: list[EscalationOutcome] = []
    tags = tuple(ticket.get("tags") or ())
    priority = ticket.get("priority")
    project_id = ticket.get("project_id")

    for rule in rules:
        if not rule.enabled:
            continue
        if rule.when.event != event:
            continue
        if rule.team_id is not None and rule.team_id != ticket_team_id:
            continue

        if rule.when.priority is not None and rule.when.priority != priority:
            continue
        if rule.when.project_id is not None and str(rule.when.project_id) != str(project_id):
            continue

        if rule.when.tag is not None:
            if event == "ticket_tagged":
                if rule.when.tag != tag_added:
                    continue
            elif rule.when.tag not in tags:
                continue

        out.append(EscalationOutcome(rule=rule))
    return out
