"""Argon2 password hashing round-trip."""

from __future__ import annotations

from xtv_support.api.password import hash_password, verify_password


def test_hash_round_trip() -> None:
    h = hash_password("correct horse battery")
    assert h != "correct horse battery"
    assert verify_password(h, "correct horse battery") is True


def test_verify_rejects_wrong_password() -> None:
    h = hash_password("longenoughpw")
    assert verify_password(h, "wrong") is False


def test_verify_never_raises_on_garbage_hash() -> None:
    assert verify_password("not-a-hash", "whatever") is False


def test_hashes_are_salted_unique() -> None:
    assert hash_password("samepw12345") != hash_password("samepw12345")
