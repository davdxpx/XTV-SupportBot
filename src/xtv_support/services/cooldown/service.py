from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from xtv_support.config.settings import settings


@dataclass
class BucketDecision:
    allowed: bool
    retry_after: int = 0


@dataclass
class CooldownService:
    """Simple sliding-window rate limiter kept in-process.

    For multi-instance deployments this should be swapped for Redis / Mongo
    TTL; for a single-process bot this is fine and avoids DB load on every
    message.
    """

    rate: int = field(default_factory=lambda: settings.COOLDOWN_RATE)
    window: int = field(default_factory=lambda: settings.COOLDOWN_WINDOW)
    mute_seconds: int = field(default_factory=lambda: settings.COOLDOWN_MUTE_SECONDS)

    _events: dict[int, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _muted_until: dict[int, float] = field(default_factory=dict)
    _strikes: dict[int, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def check(self, user_id: int) -> BucketDecision:
        async with self._lock:
            now = time.monotonic()
            # Honour an active mute first.
            muted_until = self._muted_until.get(user_id, 0)
            if muted_until > now:
                return BucketDecision(False, retry_after=int(muted_until - now) + 1)

            events = self._events[user_id]
            cutoff = now - self.window
            while events and events[0] < cutoff:
                events.popleft()

            if len(events) >= self.rate:
                self._muted_until[user_id] = now + self.mute_seconds
                events.clear()
                strikes = self._strikes[user_id]
                strikes.append(now)
                strike_cutoff = now - 3600
                while strikes and strikes[0] < strike_cutoff:
                    strikes.popleft()
                return BucketDecision(False, retry_after=self.mute_seconds)

            events.append(now)
            return BucketDecision(True)

    async def strike_count(self, user_id: int) -> int:
        async with self._lock:
            now = time.monotonic()
            strikes = self._strikes.get(user_id)
            if not strikes:
                return 0
            cutoff = now - 3600
            while strikes and strikes[0] < cutoff:
                strikes.popleft()
            return len(strikes)

    async def reset(self, user_id: int) -> None:
        async with self._lock:
            self._events.pop(user_id, None)
            self._muted_until.pop(user_id, None)
            self._strikes.pop(user_id, None)

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
