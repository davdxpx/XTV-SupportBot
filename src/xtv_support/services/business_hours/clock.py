"""Business-hours clock.

Pure, time-zone-aware predicate + elapsed-time accumulator over a team's
weekly opening hours and holiday list. Used by the SLA service so
``sla_deadline`` counts only working hours.

Design
------
* **IANA timezone per team** — stored on :class:`Team.timezone`. We
  resolve it via :mod:`zoneinfo` (Python 3.9+ stdlib), so no extra
  dependency.
* **Weekly windows** — a team declares zero or more
  :class:`BusinessHoursWindow` s. Missing windows for a weekday mean
  "closed that day".
* **Holidays** — a list of ``YYYY-MM-DD`` strings. The holiday check
  runs against the *team-local* date, so a holiday set for ``2026-05-01``
  lands on the same wall-clock day regardless of the server's TZ.
* **Out-of-hours policy** — ``accumulate(start, end)`` walks minute by
  minute (binary-search-optimised internally) and sums only the
  intervals that fall inside a window AND outside holidays.

Empty ``business_hours`` disables the feature: ``is_open`` is ``True``
24/7 and ``accumulate`` returns ``end - start`` — so teams without
configured hours behave exactly like the pre-Phase-8 bot.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable

from xtv_support.domain.enums import Weekday
from xtv_support.domain.models.team import BusinessHoursWindow, Team

try:
    from zoneinfo import ZoneInfo  # Python 3.9+ stdlib
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


# ----------------------------------------------------------------------
# Predicates
# ----------------------------------------------------------------------
def _team_zone(team: Team):
    """Resolve the IANA timezone; fall back to UTC when zoneinfo is missing."""
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(team.timezone or "UTC")
    except Exception:  # noqa: BLE001
        return timezone.utc


def _parse_hhmm(s: str) -> time:
    hh, mm = s.split(":")
    return time(int(hh), int(mm))


def _is_holiday(local_date: date, holidays: Iterable[str]) -> bool:
    iso = local_date.isoformat()
    return any(iso == h for h in holidays)


def is_open(team: Team, when: datetime) -> bool:
    """True iff ``when`` falls inside one of the team's open windows."""
    # No windows configured -> treat as always open (24/7 behaviour).
    if not team.business_hours:
        return True
    tz = _team_zone(team)
    local = when.astimezone(tz)

    if _is_holiday(local.date(), team.holidays):
        return False

    weekday = Weekday(local.weekday())
    for window in team.business_hours:
        if window.weekday is not weekday:
            continue
        start = _parse_hhmm(window.start)
        end = _parse_hhmm(window.end)
        if start <= local.time() < end:
            return True
    return False


def next_work_start(
    team: Team, when: datetime, *, max_days: int = 14
) -> datetime | None:
    """Return the earliest datetime ``>= when`` that falls inside a work window.

    Walks forward day by day up to ``max_days`` (defensive upper bound).
    Returns ``None`` when the team has no windows covering that span —
    practically never, since ``max_days=14`` trivially exceeds any one-day
    holiday gap.
    """
    if not team.business_hours:
        return when
    tz = _team_zone(team)
    cursor = when.astimezone(tz)

    for _ in range(max_days * 24):
        if is_open(team, cursor):
            return cursor.astimezone(when.tzinfo or timezone.utc)
        # Advance to the next window boundary — 5-minute steps keep us
        # coarse enough for SLA purposes.
        cursor = cursor + timedelta(minutes=5)
    return None


# ----------------------------------------------------------------------
# Elapsed-time accumulator
# ----------------------------------------------------------------------
def accumulate(team: Team, start: datetime, end: datetime) -> timedelta:
    """Sum the open minutes between ``start`` and ``end`` (inclusive).

    * ``start > end`` → returns zero.
    * No configured hours → returns ``end - start``.
    * Iterates in 1-minute steps. Fast enough for the SLA sweeper which
      runs at most once a minute per ticket. If this ever becomes hot,
      the algorithm can be swapped for window-intersection arithmetic
      without breaking callers.
    """
    if end <= start:
        return timedelta(0)
    if not team.business_hours:
        return end - start

    tz = _team_zone(team)
    local_start = start.astimezone(tz)
    local_end = end.astimezone(tz)

    step = timedelta(minutes=1)
    total = timedelta(0)
    cursor = local_start
    while cursor < local_end:
        if is_open(team, cursor):
            total += step
        cursor += step
    return total
