"""Tiny arithmetic challenge generator.

Pure — used by the plugin to build the inline-keyboard question and
to verify the user's click callback. A stateless HMAC of the user_id
+ answer lets us verify answers without persisting per-user state.
"""

from __future__ import annotations

import hashlib
import hmac
import random
import secrets
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Challenge:
    question: str
    correct: int
    options: tuple[int, ...]  # shuffled; exactly 4 items


def new_challenge() -> Challenge:
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    answer = a + b
    # Distractors within ±3, never equal to the answer.
    distractors: set[int] = set()
    while len(distractors) < 3:
        candidate = answer + random.choice([-3, -2, -1, 1, 2, 3])
        if candidate != answer and candidate > 0:
            distractors.add(candidate)
    options = [answer, *distractors]
    random.shuffle(options)
    return Challenge(
        question=f"{a} + {b} = ?",
        correct=answer,
        options=tuple(options),
    )


def sign_answer(user_id: int, answer: int, *, secret: str) -> str:
    """HMAC hex so the click callback can ship the answer without server state."""
    msg = f"{user_id}:{answer}".encode()
    return hmac.new(secret.encode(), msg=msg, digestmod=hashlib.sha256).hexdigest()[:16]


def verify(user_id: int, answer: int, token: str, *, secret: str) -> bool:
    expected = sign_answer(user_id, answer, secret=secret)
    return secrets.compare_digest(expected, token)
