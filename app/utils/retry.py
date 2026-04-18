from __future__ import annotations

import asyncio
from functools import wraps
from typing import Awaitable, Callable, TypeVar

from app.core.logger import get_logger

T = TypeVar("T")
log = get_logger("retry")


def async_retry(
    attempts: int = 3,
    backoff: float = 1.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry an async function with exponential backoff."""

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> T:
            last_exc: BaseException | None = None
            delay = 1.0
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:  # noqa: PERF203
                    last_exc = exc
                    if attempt == attempts:
                        break
                    log.warning(
                        "retry.attempt_failed",
                        fn=fn.__name__,
                        attempt=attempt,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
