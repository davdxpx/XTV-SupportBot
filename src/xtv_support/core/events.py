"""In-process async event bus.

Design goals
------------
* **Loose coupling** — services and plugins publish events; zero knowledge
  of consumers.
* **Error isolation** — one misbehaving subscriber never prevents siblings
  from running. Exceptions are logged, never re-raised.
* **Mixed sync / async handlers** — the bus detects awaitables and awaits
  them; sync handlers are called directly.
* **Typed dispatch** — events are matched by *exact* class. Subclass-aware
  dispatch is available via ``publish(..., propagate_to_bases=True)``.

The bus is deliberately tiny — no persistence, no priorities, no ordering
guarantees beyond subscription order. A future phase can swap it for a
Redis Streams / Kafka adapter without touching producers.
"""
from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from xtv_support.core.logger import get_logger
from xtv_support.domain.events.base import DomainEvent

Handler = Callable[[Any], Awaitable[None] | None]

_log = get_logger("events")


class EventBus:
    """Async pub/sub keyed by event class."""

    __slots__ = ("_handlers",)

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------
    def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> Handler:
        """Register ``handler`` for ``event_type``. Duplicate registrations are a no-op."""
        bucket = self._handlers[event_type]
        if handler not in bucket:
            bucket.append(handler)
        return handler

    def unsubscribe(self, event_type: type[DomainEvent], handler: Handler) -> bool:
        """Remove a previously-registered handler. Returns ``True`` if removed."""
        bucket = self._handlers.get(event_type)
        if not bucket or handler not in bucket:
            return False
        bucket.remove(handler)
        if not bucket:
            del self._handlers[event_type]
        return True

    def on(self, event_type: type[DomainEvent]) -> Callable[[Handler], Handler]:
        """Decorator form of :meth:`subscribe`.

        ``python
        @bus.on(TicketCreated)
        async def alert_admins(event: TicketCreated) -> None:
            ...
        ``
        """

        def decorator(handler: Handler) -> Handler:
            return self.subscribe(event_type, handler)

        return decorator

    def clear(self) -> None:
        """Drop every registration. Intended for tests only."""
        self._handlers.clear()

    def handler_count(self, event_type: type[DomainEvent] | None = None) -> int:
        """Number of registered handlers (total, or for one event type)."""
        if event_type is None:
            return sum(len(v) for v in self._handlers.values())
        return len(self._handlers.get(event_type, []))

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    async def publish(
        self,
        event: DomainEvent,
        *,
        propagate_to_bases: bool = False,
    ) -> None:
        """Dispatch ``event`` to every subscribed handler.

        Parameters
        ----------
        event:
            The immutable event instance to deliver.
        propagate_to_bases:
            When True, handlers registered against any base class of
            ``type(event)`` (excluding :class:`DomainEvent` itself) also
            receive the event. Defaults to False — strict exact-type match.
        """
        handlers = self._resolve_handlers(type(event), propagate_to_bases)
        if not handlers:
            return

        # Run all handlers concurrently; each one is isolated by _run.
        await asyncio.gather(*(self._run(h, event) for h in handlers))

    def _resolve_handlers(
        self, event_type: type[DomainEvent], propagate: bool
    ) -> list[Handler]:
        if not propagate:
            return list(self._handlers.get(event_type, ()))
        out: list[Handler] = []
        seen: set[int] = set()
        for klass in event_type.__mro__:
            if klass is object or klass is DomainEvent:
                continue
            for h in self._handlers.get(klass, ()):
                key = id(h)
                if key in seen:
                    continue
                seen.add(key)
                out.append(h)
        return out

    @staticmethod
    async def _run(handler: Handler, event: DomainEvent) -> None:
        """Invoke one handler, swallowing and logging any exception."""
        try:
            result = handler(event)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:  # noqa: BLE001 — we want *everything* contained
            _log.exception(
                "event.handler_failed",
                evt_type=type(event).__name__,
                evt_id=getattr(event, "event_id", None),
                handler=getattr(handler, "__qualname__", repr(handler)),
                error=str(exc),
            )
