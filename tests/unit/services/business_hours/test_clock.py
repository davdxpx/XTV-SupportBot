"""Business-hours clock tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from xtv_support.domain.enums import Weekday
from xtv_support.domain.models.team import BusinessHoursWindow, Team
from xtv_support.services.business_hours.clock import (
    accumulate,
    is_open,
    next_work_start,
)


def _team(
    *,
    tz: str = "UTC",
    windows: list[BusinessHoursWindow] | None = None,
    holidays: list[str] | None = None,
) -> Team:
    return Team(
        id="support",
        name="Support",
        timezone=tz,
        business_hours=tuple(windows or []),
        holidays=tuple(holidays or []),
    )


def _dt(y, m, d, H=0, M=0) -> datetime:
    return datetime(y, m, d, H, M, tzinfo=UTC)


# ----------------------------------------------------------------------
# is_open / empty windows
# ----------------------------------------------------------------------
def test_empty_windows_are_always_open() -> None:
    team = _team()
    assert is_open(team, _dt(2026, 4, 23, 3, 0))  # 3 AM
    assert is_open(team, _dt(2026, 4, 26, 2, 0))  # Sunday


def test_is_open_within_window() -> None:
    team = _team(
        windows=[BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="17:00")],
    )
    # 2026-04-20 is a Monday.
    assert is_open(team, _dt(2026, 4, 20, 10, 30))
    assert is_open(team, _dt(2026, 4, 20, 9, 0))  # inclusive start
    assert not is_open(team, _dt(2026, 4, 20, 17, 0))  # exclusive end
    assert not is_open(team, _dt(2026, 4, 20, 8, 59))


def test_is_open_different_weekday_closed() -> None:
    team = _team(
        windows=[BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="17:00")],
    )
    assert not is_open(team, _dt(2026, 4, 21, 10, 0))  # Tuesday


def test_holidays_close_the_day() -> None:
    team = _team(
        windows=[BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="17:00")],
        holidays=["2026-04-20"],
    )
    assert not is_open(team, _dt(2026, 4, 20, 10, 0))


def test_timezone_shift_matters() -> None:
    # 2026-04-20 23:00 UTC == 2026-04-21 01:00 Europe/Berlin (CEST).
    # Monday 17:00 Berlin ends at 15:00 UTC.
    team = _team(
        tz="Europe/Berlin",
        windows=[BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="17:00")],
    )
    assert is_open(team, _dt(2026, 4, 20, 8, 0))  # 10:00 Berlin -> open
    assert not is_open(team, _dt(2026, 4, 20, 15, 0))  # 17:00 Berlin -> closed


# ----------------------------------------------------------------------
# accumulate
# ----------------------------------------------------------------------
def test_accumulate_zero_when_end_before_start() -> None:
    team = _team()
    result = accumulate(team, _dt(2026, 4, 20, 10, 0), _dt(2026, 4, 20, 9, 0))
    assert result == timedelta(0)


def test_accumulate_empty_windows_returns_full_interval() -> None:
    team = _team()
    result = accumulate(team, _dt(2026, 4, 20, 10, 0), _dt(2026, 4, 20, 12, 0))
    assert result == timedelta(hours=2)


def test_accumulate_skips_closed_time() -> None:
    team = _team(
        windows=[
            BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="12:00"),
        ],
    )
    # 08:00 -> 13:00: only 09:00-12:00 counts = 3h
    result = accumulate(team, _dt(2026, 4, 20, 8, 0), _dt(2026, 4, 20, 13, 0))
    assert result == timedelta(hours=3)


def test_accumulate_crosses_holiday() -> None:
    team = _team(
        windows=[
            BusinessHoursWindow(weekday=Weekday.MONDAY, start="09:00", end="12:00"),
        ],
        holidays=["2026-04-20"],
    )
    result = accumulate(team, _dt(2026, 4, 20, 9, 0), _dt(2026, 4, 20, 12, 0))
    assert result == timedelta(0)


# ----------------------------------------------------------------------
# next_work_start
# ----------------------------------------------------------------------
def test_next_work_start_returns_input_when_already_open() -> None:
    team = _team()
    when = _dt(2026, 4, 20, 10, 0)
    assert next_work_start(team, when) == when


def test_next_work_start_finds_next_open_window() -> None:
    team = _team(
        windows=[BusinessHoursWindow(weekday=Weekday.TUESDAY, start="09:00", end="17:00")],
    )
    # Monday 10:00 -> must jump to Tuesday 09:00.
    result = next_work_start(team, _dt(2026, 4, 20, 10, 0))
    assert result is not None
    assert result.weekday() == Weekday.TUESDAY
    # Within 5 min of 09:00 (step size of the walk).
    assert result.hour == 9
    assert result.minute <= 5
