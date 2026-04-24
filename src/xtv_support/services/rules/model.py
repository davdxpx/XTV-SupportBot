"""Rule data-model.

Rules are stored in the ``automation_rules`` Mongo collection with
versioning: every save bumps ``version`` and keeps the previous
payload in the ``history`` array so operators can audit / rollback.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class Condition:
    """One predicate — evaluated AND-joined with siblings.

    ``field`` addresses a path on the ticket document (``priority``,
    ``tags``, ``project_id``, ``team_id``, ``assignee_id``). ``op`` is
    a small fixed set to keep the language safe: ``eq``, ``ne``,
    ``in``, ``not_in``, ``contains`` (list contains), ``gt``, ``lt``.
    """

    field: str
    op: str
    value: str | int | float | bool | tuple | list


@dataclass(frozen=True, slots=True, kw_only=True)
class ActionRef:
    """A concrete ActionExecutor invocation — name + params dict."""

    name: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class Rule:
    id: str
    name: str
    enabled: bool
    trigger: str  # event class name, e.g. "TicketCreated" / "SlaBreached"
    conditions: tuple[Condition, ...] = field(default_factory=tuple)
    actions: tuple[ActionRef, ...] = field(default_factory=tuple)
    cooldown_s: int = 0
    max_fires_per_day: int | None = None
    version: int = 1
    created_by: int | None = None


def condition_matches(cond: Condition, ticket: dict) -> bool:
    """Pure predicate evaluation. Unknown op → no match."""
    value = _walk(ticket, cond.field)
    op = cond.op
    if op == "eq":
        return value == cond.value
    if op == "ne":
        return value != cond.value
    if op == "in":
        return value in (cond.value or ())
    if op == "not_in":
        return value not in (cond.value or ())
    if op == "contains":
        try:
            return cond.value in (value or [])
        except TypeError:
            return False
    if op == "gt":
        try:
            return value is not None and value > cond.value  # type: ignore[operator]
        except TypeError:
            return False
    if op == "lt":
        try:
            return value is not None and value < cond.value  # type: ignore[operator]
        except TypeError:
            return False
    return False


def _walk(doc: dict, path: str):
    cur: object = doc
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def all_conditions_match(conds: tuple[Condition, ...], ticket: dict) -> bool:
    return all(condition_matches(c, ticket) for c in conds)
