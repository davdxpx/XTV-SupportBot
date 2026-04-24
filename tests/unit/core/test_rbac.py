"""RBAC permission-matrix + resolver tests.

The pure decision logic + DB-backed resolver live in
:mod:`xtv_support.core.rbac`; this file exercises them directly with
no pyrofork dependency. The pyrofork glue in
:mod:`xtv_support.middlewares.rbac_mw` is a three-line wrapper.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from xtv_support.core.errors import AdminOnly
from xtv_support.core.rbac import current, current_role, decide, require, resolve_role
from xtv_support.domain.enums import Role
from xtv_support.domain.models.role import RoleAssignment


# ----------------------------------------------------------------------
# decide() — pure permission matrix.
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "actual,required,expected",
    [
        # Exact-match cases
        (Role.ADMIN, [Role.ADMIN], True),
        (Role.USER, [Role.USER], True),
        # Higher passes lower
        (Role.OWNER, [Role.ADMIN], True),
        (Role.ADMIN, [Role.SUPERVISOR], True),
        (Role.SUPERVISOR, [Role.AGENT], True),
        (Role.AGENT, [Role.USER], True),
        # Lower fails higher
        (Role.USER, [Role.AGENT], False),
        (Role.AGENT, [Role.SUPERVISOR], False),
        (Role.ADMIN, [Role.OWNER], False),
        # Multiple requirements act as OR (lowest threshold wins)
        (Role.AGENT, [Role.ADMIN, Role.AGENT], True),
        (Role.VIEWER, [Role.ADMIN, Role.AGENT], False),
        # Empty requirement -> always allow
        (Role.USER, [], True),
    ],
)
def test_decide_matrix(actual: Role, required: list[Role], expected: bool) -> None:
    assert decide(actual, required) is expected


# ----------------------------------------------------------------------
# require() — uses the ContextVar.
# ----------------------------------------------------------------------
def test_require_passes_when_context_has_sufficient_role() -> None:
    token = current_role.set(Role.ADMIN)
    try:
        require(Role.SUPERVISOR)  # must not raise
        require(Role.ADMIN)
    finally:
        current_role.reset(token)


def test_require_raises_admin_only_when_insufficient() -> None:
    token = current_role.set(Role.AGENT)
    try:
        with pytest.raises(AdminOnly):
            require(Role.ADMIN)
    finally:
        current_role.reset(token)


def test_current_returns_contextvar_value() -> None:
    assert current() is Role.USER  # default

    token = current_role.set(Role.OWNER)
    try:
        assert current() is Role.OWNER
    finally:
        current_role.reset(token)


# ----------------------------------------------------------------------
# resolve_role() — DB lookup with legacy fallback.
# ----------------------------------------------------------------------
@pytest.fixture
def _patch_repo(monkeypatch: pytest.MonkeyPatch):
    """Patch the lazy-imported roles_repo used inside resolve_role."""
    from xtv_support.infrastructure.db import roles as roles_repo

    mock = AsyncMock()
    monkeypatch.setattr(roles_repo, "get_role", mock, raising=True)
    return mock


async def test_resolve_uses_db_role_when_present(_patch_repo) -> None:
    db = SimpleNamespace()
    _patch_repo.return_value = RoleAssignment(user_id=7, role=Role.SUPERVISOR)

    role = await resolve_role(db, 7, legacy_admin_ids=[])
    assert role is Role.SUPERVISOR
    _patch_repo.assert_awaited_once_with(db, 7)


async def test_resolve_falls_back_to_admin_ids(_patch_repo) -> None:
    db = SimpleNamespace()
    _patch_repo.return_value = None

    assert await resolve_role(db, 99, legacy_admin_ids=[99, 100]) is Role.ADMIN
    assert await resolve_role(db, 999, legacy_admin_ids=[99, 100]) is Role.USER


async def test_resolve_survives_db_errors(_patch_repo) -> None:
    db = SimpleNamespace()
    _patch_repo.side_effect = RuntimeError("mongo down")

    # Must not raise — returns the default Role.USER.
    assert await resolve_role(db, 1, legacy_admin_ids=[]) is Role.USER
