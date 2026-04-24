"""Minimal dependency-injection container.

Goals
-----
* Replace the hand-wired :class:`~xtv_support.core.context.HandlerContext`
  by a lookup-based registry so services / plugins resolve collaborators
  by type without knowing how they are built.
* Keep the surface tiny — no interceptors, no scopes beyond
  ``singleton`` vs ``factory``, no lifetime other than process-lifetime.
* Detect cyclic resolution paths (A -> B -> A) instead of silently
  looping forever.

Usage
-----
``python
c = Container()
c.register(Settings, lambda _c: Settings())
c.register_instance(EventBus, EventBus())

# Factory that depends on other registered types:
def make_ticket_service(c: Container) -> TicketService:
    return TicketService(db=c.resolve(Database), bus=c.resolve(EventBus))

c.register(TicketService, make_ticket_service)

svc = c.resolve(TicketService)
``
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeVar

T = TypeVar("T")

Factory = Callable[["Container"], Any]


class ContainerError(RuntimeError):
    """Base class for all DI-container errors."""


class NotRegisteredError(ContainerError):
    """Raised when :meth:`Container.resolve` cannot find ``key``."""


class CircularDependencyError(ContainerError):
    """Raised when a factory re-enters a currently-resolving key."""


class DuplicateRegistrationError(ContainerError):
    """Raised when ``override=False`` and ``key`` is already registered."""


# Per-container resolution stack, captured via ContextVar so nested async
# resolutions do not bleed across tasks.
_resolving: ContextVar[tuple[type, ...]] = ContextVar("_resolving", default=())


class Container:
    """Tiny, typed DI registry."""

    __slots__ = ("_factories", "_singletons", "_is_singleton")

    def __init__(self) -> None:
        self._factories: dict[type, Factory] = {}
        self._singletons: dict[type, Any] = {}
        self._is_singleton: dict[type, bool] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(
        self,
        key: type[T],
        factory: Factory,
        *,
        singleton: bool = True,
        override: bool = False,
    ) -> None:
        """Register ``factory`` for ``key``.

        Parameters
        ----------
        key:
            The *type* consumers resolve by. No string keys to keep it
            statically analysable.
        factory:
            Callable of ``(container) -> T``. Runs lazily on first
            ``resolve`` when ``singleton=True``, or on every call when
            ``singleton=False``.
        singleton:
            When True (default) the factory runs once and the result is
            cached. When False, every ``resolve`` builds a fresh instance.
        override:
            When False (default) re-registering an existing key raises.
            Set True in tests to swap implementations.
        """
        if not override and key in self._factories:
            raise DuplicateRegistrationError(
                f"{key.__name__} is already registered; pass override=True to replace."
            )
        self._factories[key] = factory
        self._is_singleton[key] = singleton
        # Drop any cached singleton from a previous registration.
        self._singletons.pop(key, None)

    def register_instance(self, key: type[T], instance: T, *, override: bool = False) -> None:
        """Shortcut for ``register(key, lambda _c: instance, singleton=True)``."""
        if not override and key in self._factories:
            raise DuplicateRegistrationError(
                f"{key.__name__} is already registered; pass override=True to replace."
            )
        self._factories[key] = lambda _c: instance
        self._is_singleton[key] = True
        self._singletons[key] = instance

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    def resolve(self, key: type[T]) -> T:
        """Return an instance of ``key`` or raise."""
        if key in self._singletons:
            return self._singletons[key]  # type: ignore[no-any-return]

        factory = self._factories.get(key)
        if factory is None:
            raise NotRegisteredError(f"{key.__name__} has not been registered.")

        stack = _resolving.get()
        if key in stack:
            chain = " -> ".join(k.__name__ for k in (*stack, key))
            raise CircularDependencyError(f"Circular dependency: {chain}")

        token = _resolving.set((*stack, key))
        try:
            value = factory(self)
        finally:
            _resolving.reset(token)

        if self._is_singleton.get(key, True):
            self._singletons[key] = value
        return value  # type: ignore[no-any-return]

    def try_resolve(self, key: type[T]) -> T | None:
        """Return an instance, or ``None`` if not registered."""
        try:
            return self.resolve(key)
        except NotRegisteredError:
            return None

    # ------------------------------------------------------------------
    # Introspection / lifecycle
    # ------------------------------------------------------------------
    def is_registered(self, key: type) -> bool:
        return key in self._factories

    def keys(self) -> list[type]:
        """Stable-ordered snapshot of every registered key."""
        return list(self._factories.keys())

    def clear(self) -> None:
        """Drop every factory + cached singleton. Intended for tests."""
        self._factories.clear()
        self._singletons.clear()
        self._is_singleton.clear()
