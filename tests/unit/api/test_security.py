"""API-key helpers tests — pure hashing + scope logic."""
from __future__ import annotations

import pytest

from xtv_support.api.security import (
    KEY_LENGTH,
    KEY_PREFIX,
    SCOPES,
    generate_key,
    hash_key,
    scope_satisfies,
)


# ----------------------------------------------------------------------
# hash + generate
# ----------------------------------------------------------------------
def test_hash_is_deterministic() -> None:
    assert hash_key("foo") == hash_key("foo")
    assert hash_key("foo") != hash_key("bar")


def test_generate_key_has_prefix() -> None:
    key = generate_key()
    assert key.startswith(KEY_PREFIX)


def test_generate_key_length() -> None:
    key = generate_key()
    # prefix + 40-char body
    assert len(key) == len(KEY_PREFIX) + KEY_LENGTH


def test_generate_keys_are_unique() -> None:
    batch = {generate_key() for _ in range(100)}
    assert len(batch) == 100


# ----------------------------------------------------------------------
# scope_satisfies
# ----------------------------------------------------------------------
def test_admin_full_grants_everything() -> None:
    assert scope_satisfies(("admin:full",), "tickets:write")
    assert scope_satisfies(("admin:full",), "projects:read")


def test_exact_scope_match() -> None:
    assert scope_satisfies(("tickets:read",), "tickets:read")
    assert not scope_satisfies(("tickets:read",), "tickets:write")


def test_scope_disjunction() -> None:
    key_scopes = ("tickets:read", "analytics:read")
    assert scope_satisfies(key_scopes, "analytics:read")
    assert not scope_satisfies(key_scopes, "webhooks:write")


def test_empty_scopes_grants_nothing() -> None:
    assert not scope_satisfies((), "tickets:read")


# ----------------------------------------------------------------------
# known scopes contract
# ----------------------------------------------------------------------
@pytest.mark.parametrize("s", SCOPES)
def test_all_known_scopes_have_a_colon(s: str) -> None:
    assert ":" in s


def test_known_scopes_include_admin_full() -> None:
    assert "admin:full" in SCOPES
