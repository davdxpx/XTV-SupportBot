from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.core.logger import get_logger

log = get_logger("scheduler")


@dataclass
class TaskManager:
    """Tracks and cancels long-running asyncio tasks."""

    _tasks: list[asyncio.Task] = field(default_factory=list)
    _stopped: bool = False

    async def start(self) -> None:
        log.info("scheduler.start")

    def spawn(self, coro: Awaitable, *, name: str) -> asyncio.Task:
        task = asyncio.create_task(coro, name=name)
        self._tasks.append(task)
        log.info("scheduler.spawned", name=name)
        return task

    def run_loop(
        self,
        fn: Callable[[], Awaitable[None]],
        *,
        name: str,
        interval: float,
        jitter: float = 0.0,
    ) -> asyncio.Task:
        async def _loop() -> None:
            import random

            while not self._stopped:
                try:
                    await fn()
                except Exception as exc:  # noqa: BLE001
                    log.exception("scheduler.loop_error", name=name, error=str(exc))
                wait = interval + random.random() * jitter
                try:
                    await asyncio.sleep(wait)
                except asyncio.CancelledError:
                    return

        return self.spawn(_loop(), name=name)

    async def stop(self) -> None:
        self._stopped = True
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        log.info("scheduler.stop", tasks=len(self._tasks))
        self._tasks.clear()

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
