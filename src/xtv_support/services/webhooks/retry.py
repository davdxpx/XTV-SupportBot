"""Retry-schedule helpers for webhook deliveries.

Separated from the sender so the exponential-backoff policy can be
unit-tested without an HTTP client in the loop.
"""
from __future__ import annotations

MAX_ATTEMPTS = 5

# Delays in seconds: ~5s, 30s, 2m, 10m, 1h. After attempt 5 the
# webhook is marked inactive and the queue drops the event.
DELAYS: tuple[int, ...] = (5, 30, 120, 600, 3600)


def next_delay(attempt: int) -> int | None:
    """Return the delay before the next retry, or ``None`` when exhausted.

    ``attempt`` is 1-based: the first failure calls ``next_delay(1)``
    and expects the first entry in :data:`DELAYS`.
    """
    if attempt < 1 or attempt >= MAX_ATTEMPTS:
        return None
    return DELAYS[attempt - 1]


def should_disable(attempt: int) -> bool:
    """After this many failed attempts, the caller disables the webhook."""
    return attempt >= MAX_ATTEMPTS
