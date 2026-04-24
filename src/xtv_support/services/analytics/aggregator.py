"""Analytics aggregator — pure computations over raw ticket docs.

These functions accept iterables of ticket dicts (straight out of
Mongo) + optional aux data and return structured stats dataclasses.
Keeping them pure lets us test exhaustively without any DB and lets
the REST API, the digest plugin, and the /admin dashboard share the
same numbers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import median


# ----------------------------------------------------------------------
# Result types
# ----------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class TicketVolume:
    """Ticket counts split by dimension for a time range."""

    total: int
    by_day: dict[str, int] = field(default_factory=dict)  # YYYY-MM-DD
    by_project: dict[str, int] = field(default_factory=dict)
    by_team: dict[str, int] = field(default_factory=dict)
    by_priority: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResponseTimes:
    """First-response + resolution-time distribution in seconds."""

    first_response_median: float | None
    first_response_p90: float | None
    resolution_median: float | None
    resolution_p90: float | None
    samples: int


@dataclass(frozen=True, slots=True)
class SlaCompliance:
    breached: int
    total: int

    @property
    def compliance_ratio(self) -> float:
        if self.total == 0:
            return 1.0
        return round(1 - (self.breached / self.total), 3)


@dataclass(frozen=True, slots=True)
class AgentLeaderboardRow:
    agent_id: int
    closed: int
    avg_resolution_seconds: float | None
    csat_average: float | None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _to_utc_date(value) -> str | None:
    if not isinstance(value, datetime):
        return None
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).date().isoformat()


def _pct(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((pct / 100.0) * (len(values) - 1)))))
    return round(values[k], 2)


# ----------------------------------------------------------------------
# Aggregators
# ----------------------------------------------------------------------
def compute_volume(tickets: Iterable[Mapping]) -> TicketVolume:
    by_day: Counter[str] = Counter()
    by_project: Counter[str] = Counter()
    by_team: Counter[str] = Counter()
    by_priority: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    total = 0
    for t in tickets:
        total += 1
        day = _to_utc_date(t.get("created_at"))
        if day:
            by_day[day] += 1
        if t.get("project_id") is not None:
            by_project[str(t["project_id"])] += 1
        if t.get("team_id") is not None:
            by_team[str(t["team_id"])] += 1
        if t.get("priority"):
            by_priority[str(t["priority"])] += 1
        if t.get("status"):
            by_status[str(t["status"])] += 1
    return TicketVolume(
        total=total,
        by_day=dict(by_day),
        by_project=dict(by_project),
        by_team=dict(by_team),
        by_priority=dict(by_priority),
        by_status=dict(by_status),
    )


def compute_response_times(tickets: Iterable[Mapping]) -> ResponseTimes:
    """Median + p90 for first-response + resolution in seconds.

    First-response time: ``last_admin_msg_at - created_at`` when both
    exist. Resolution time: ``closed_at - created_at`` when closed.
    Tickets missing the relevant timestamps are skipped.
    """
    frt: list[float] = []
    res: list[float] = []
    samples = 0
    for t in tickets:
        samples += 1
        created = t.get("created_at")
        first_admin = t.get("last_admin_msg_at")
        closed = t.get("closed_at")
        if isinstance(created, datetime) and isinstance(first_admin, datetime):
            delta = (first_admin - created).total_seconds()
            if delta >= 0:
                frt.append(delta)
        if isinstance(created, datetime) and isinstance(closed, datetime):
            delta = (closed - created).total_seconds()
            if delta >= 0:
                res.append(delta)

    frt_med = round(median(frt), 2) if frt else None
    res_med = round(median(res), 2) if res else None
    return ResponseTimes(
        first_response_median=frt_med,
        first_response_p90=_pct(frt, 90),
        resolution_median=res_med,
        resolution_p90=_pct(res, 90),
        samples=samples,
    )


def compute_sla_compliance(tickets: Iterable[Mapping]) -> SlaCompliance:
    breached = 0
    total = 0
    for t in tickets:
        deadline = t.get("sla_deadline")
        closed = t.get("closed_at")
        if not isinstance(deadline, datetime):
            continue
        total += 1
        # Breached when closed (or current time) > deadline.
        if (
            isinstance(closed, datetime)
            and closed > deadline
            or closed is None
            and datetime.now(UTC) > deadline
        ):
            breached += 1
    return SlaCompliance(breached=breached, total=total)


def compute_agent_leaderboard(
    tickets: Iterable[Mapping],
    *,
    csat_by_agent: Mapping[int, list[int]] | None = None,
    top: int = 10,
) -> list[AgentLeaderboardRow]:
    """Rank agents by closed-ticket count with supporting metrics."""
    closed_per_agent: defaultdict[int, int] = defaultdict(int)
    res_times: defaultdict[int, list[float]] = defaultdict(list)
    for t in tickets:
        if t.get("status") != "closed":
            continue
        agent = t.get("assignee_id") or t.get("closed_by")
        if not isinstance(agent, int):
            continue
        closed_per_agent[agent] += 1
        created = t.get("created_at")
        closed = t.get("closed_at")
        if isinstance(created, datetime) and isinstance(closed, datetime):
            res_times[agent].append((closed - created).total_seconds())

    rows: list[AgentLeaderboardRow] = []
    for agent, count in closed_per_agent.items():
        avg_res = (
            round(sum(res_times[agent]) / len(res_times[agent]), 2) if res_times[agent] else None
        )
        scores = (csat_by_agent or {}).get(agent) or []
        csat_avg = round(sum(scores) / len(scores), 2) if scores else None
        rows.append(
            AgentLeaderboardRow(
                agent_id=agent,
                closed=count,
                avg_resolution_seconds=avg_res,
                csat_average=csat_avg,
            )
        )
    rows.sort(key=lambda r: (-r.closed, r.agent_id))
    return rows[:top]
