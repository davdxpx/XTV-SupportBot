"""Minimal in-process sliding-window rate limiter for the login route.

Keyed by ``ip|username`` so neither a single IP nor a single targeted
account can be brute-forced. **Per-process only** — under horizontal
scale-out (multiple bot replicas) each replica keeps its own window, so
the effective limit multiplies by the replica count. Acceptable for the
current single-process deployment; revisit with a shared store (Redis)
if the API is ever scaled out.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_WINDOW_SECONDS = 15 * 60
_MAX_ATTEMPTS = 10

_lock = threading.Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


def check_and_record(key: str, *, now: float | None = None) -> bool:
    """Record an attempt for ``key``; return True if allowed, False if throttled."""
    ts = now if now is not None else time.monotonic()
    cutoff = ts - _WINDOW_SECONDS
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= _MAX_ATTEMPTS:
            return False
        bucket.append(ts)
        return True


def reset() -> None:
    """Clear all buckets — test helper."""
    with _lock:
        _buckets.clear()


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
