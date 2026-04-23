"""Start-captcha challenge tests."""
from __future__ import annotations

from xtv_support.plugins.builtin.start_captcha.challenge import (
    new_challenge,
    sign_answer,
    verify,
)


def test_challenge_has_four_options_including_answer() -> None:
    c = new_challenge()
    assert len(c.options) == 4
    assert c.correct in c.options


def test_challenge_question_shape() -> None:
    c = new_challenge()
    assert "+" in c.question
    assert "=" in c.question


def test_sign_is_deterministic() -> None:
    t1 = sign_answer(99, 13, secret="k")
    t2 = sign_answer(99, 13, secret="k")
    assert t1 == t2 and len(t1) == 16


def test_sign_differs_with_secret() -> None:
    t1 = sign_answer(99, 13, secret="k1")
    t2 = sign_answer(99, 13, secret="k2")
    assert t1 != t2


def test_verify_round_trip() -> None:
    t = sign_answer(99, 13, secret="k")
    assert verify(99, 13, t, secret="k")


def test_verify_rejects_wrong_answer() -> None:
    t = sign_answer(99, 13, secret="k")
    assert not verify(99, 14, t, secret="k")


def test_verify_rejects_wrong_user() -> None:
    t = sign_answer(99, 13, secret="k")
    assert not verify(100, 13, t, secret="k")


def test_verify_rejects_wrong_secret() -> None:
    t = sign_answer(99, 13, secret="right")
    assert not verify(99, 13, t, secret="wrong")
