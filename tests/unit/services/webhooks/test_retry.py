"""Retry-policy tests."""

from __future__ import annotations

import pytest

from xtv_support.services.webhooks.retry import (
    DELAYS,
    MAX_ATTEMPTS,
    next_delay,
    should_disable,
)


def test_delays_sequence_is_monotonic() -> None:
    # Each retry must wait longer than the previous.
    assert list(DELAYS) == sorted(DELAYS)


@pytest.mark.parametrize("attempt,expected", list(enumerate(DELAYS, start=1)))
def test_next_delay_follows_delays(attempt: int, expected: int) -> None:
    # Except for the last attempt, which has no next retry.
    if attempt >= MAX_ATTEMPTS:
        assert next_delay(attempt) is None
    else:
        assert next_delay(attempt) == expected


def test_next_delay_zero_and_negative_attempts_disabled() -> None:
    assert next_delay(0) is None
    assert next_delay(-1) is None


def test_should_disable_at_max_attempts() -> None:
    for a in range(1, MAX_ATTEMPTS):
        assert not should_disable(a)
    assert should_disable(MAX_ATTEMPTS)
    assert should_disable(MAX_ATTEMPTS + 1)
