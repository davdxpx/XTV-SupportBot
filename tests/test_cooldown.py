from __future__ import annotations

import pytest

from xtv_support.services.cooldown.service import CooldownService


@pytest.mark.asyncio
async def test_within_rate_allowed():
    svc = CooldownService(rate=5, window=60, mute_seconds=10)
    for _ in range(5):
        decision = await svc.check(user_id=1)
        assert decision.allowed


@pytest.mark.asyncio
async def test_burst_triggers_mute():
    svc = CooldownService(rate=3, window=60, mute_seconds=2)
    for _ in range(3):
        d = await svc.check(1)
        assert d.allowed
    # Fourth call should trigger a mute.
    d = await svc.check(1)
    assert not d.allowed
    assert d.retry_after > 0


@pytest.mark.asyncio
async def test_mute_clears_after_reset():
    svc = CooldownService(rate=2, window=60, mute_seconds=60)
    for _ in range(2):
        await svc.check(7)
    blocked = await svc.check(7)
    assert not blocked.allowed
    await svc.reset(7)
    again = await svc.check(7)
    assert again.allowed


@pytest.mark.asyncio
async def test_runtime_override_tightens_rate():
    # Service constructed permissively, but a live (runtime) override of rate=2
    # must take effect on the very next check — proves settings apply without a
    # restart of the singleton.
    svc = CooldownService(rate=100, window=60, mute_seconds=5)
    assert (await svc.check(1, rate=2, window=60, mute=5)).allowed
    assert (await svc.check(1, rate=2, window=60, mute=5)).allowed
    blocked = await svc.check(1, rate=2, window=60, mute=5)
    assert not blocked.allowed


@pytest.mark.asyncio
async def test_strikes_isolated_per_user():
    svc = CooldownService(rate=2, window=60, mute_seconds=30)
    for _ in range(2):
        await svc.check(10)
    assert not (await svc.check(10)).allowed
    # Second user is untouched.
    assert (await svc.check(99)).allowed


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
