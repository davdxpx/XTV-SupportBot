"""Container DI-registry tests."""
from __future__ import annotations

import pytest

from xtv_support.core.container import (
    CircularDependencyError,
    Container,
    DuplicateRegistrationError,
    NotRegisteredError,
)


class _A:
    pass


class _B:
    def __init__(self, a: _A) -> None:
        self.a = a


class _Cyclic:
    pass


@pytest.fixture
def c() -> Container:
    return Container()


def test_register_and_resolve_singleton(c: Container) -> None:
    c.register(_A, lambda _c: _A())
    a1 = c.resolve(_A)
    a2 = c.resolve(_A)
    assert a1 is a2


def test_register_factory_not_singleton(c: Container) -> None:
    c.register(_A, lambda _c: _A(), singleton=False)
    assert c.resolve(_A) is not c.resolve(_A)


def test_register_instance_round_trip(c: Container) -> None:
    a = _A()
    c.register_instance(_A, a)
    assert c.resolve(_A) is a


def test_factory_receives_container_and_can_resolve_deps(c: Container) -> None:
    c.register(_A, lambda _c: _A())
    c.register(_B, lambda ct: _B(ct.resolve(_A)))
    b = c.resolve(_B)
    assert isinstance(b.a, _A)
    # Deps are cached as singletons too.
    assert b.a is c.resolve(_A)


def test_resolve_unknown_raises(c: Container) -> None:
    with pytest.raises(NotRegisteredError):
        c.resolve(_A)


def test_try_resolve_returns_none_for_unknown(c: Container) -> None:
    assert c.try_resolve(_A) is None


def test_duplicate_registration_without_override_raises(c: Container) -> None:
    c.register(_A, lambda _c: _A())
    with pytest.raises(DuplicateRegistrationError):
        c.register(_A, lambda _c: _A())


def test_override_replaces_factory_and_drops_singleton_cache(c: Container) -> None:
    a1 = _A()
    c.register_instance(_A, a1)
    assert c.resolve(_A) is a1

    a2 = _A()
    c.register_instance(_A, a2, override=True)
    assert c.resolve(_A) is a2


def test_circular_dependency_is_detected(c: Container) -> None:
    def make_cyclic(ct: Container) -> _Cyclic:
        # triggers a resolve of itself — classic cycle
        ct.resolve(_Cyclic)
        return _Cyclic()

    c.register(_Cyclic, make_cyclic)
    with pytest.raises(CircularDependencyError):
        c.resolve(_Cyclic)


def test_is_registered_and_keys(c: Container) -> None:
    assert not c.is_registered(_A)
    c.register(_A, lambda _c: _A())
    c.register(_B, lambda ct: _B(ct.resolve(_A)))
    assert c.is_registered(_A) and c.is_registered(_B)
    assert {_A, _B} <= set(c.keys())


def test_clear_removes_everything(c: Container) -> None:
    c.register(_A, lambda _c: _A())
    c.resolve(_A)
    c.clear()
    assert not c.is_registered(_A)
    assert c.try_resolve(_A) is None
