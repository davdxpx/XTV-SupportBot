"""Signature verification for the Telegram WebApp ``initData``."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from xtv_support.api.auth_webapp import (
    DEFAULT_MAX_AGE,
    InvalidInitData,
    verify_init_data,
)

_BOT_TOKEN = "123456:ABC-def_1234567890"


def _sign(pairs: list[tuple[str, str]], bot_token: str = _BOT_TOKEN) -> str:
    """Helper that builds a correctly signed ``initData`` query string."""
    filtered = sorted((k, v) for k, v in pairs if k != "hash")
    data_check = "\n".join(f"{k}={v}" for k, v in filtered)
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode(filtered + [("hash", h)])


def _valid_pairs(user_id: int = 42, auth_date: int | None = None) -> list[tuple[str, str]]:
    return [
        (
            "user",
            json.dumps(
                {
                    "id": user_id,
                    "first_name": "Luca",
                    "username": "luca_test",
                    "language_code": "en",
                }
            ),
        ),
        ("auth_date", str(auth_date if auth_date is not None else int(time.time()))),
        ("query_id", "AAHdF6IQAAAAAN0XohA6f4-H"),
    ]


def test_valid_signature_returns_user() -> None:
    raw = _sign(_valid_pairs(user_id=42))
    user = verify_init_data(raw, bot_token=_BOT_TOKEN)
    assert user.id == 42
    assert user.first_name == "Luca"
    assert user.username == "luca_test"
    assert user.language_code == "en"


def test_empty_input_rejected() -> None:
    with pytest.raises(InvalidInitData, match="empty_init_data"):
        verify_init_data("", bot_token=_BOT_TOKEN)


def test_missing_hash_rejected() -> None:
    raw = urlencode(_valid_pairs())
    with pytest.raises(InvalidInitData, match="missing_hash"):
        verify_init_data(raw, bot_token=_BOT_TOKEN)


def test_bad_signature_rejected() -> None:
    raw = _sign(_valid_pairs())
    # Tamper with the user JSON after signing — the hash no longer matches.
    tampered = raw.replace("Luca", "Mallory")
    with pytest.raises(InvalidInitData, match="bad_signature"):
        verify_init_data(tampered, bot_token=_BOT_TOKEN)


def test_wrong_bot_token_rejected() -> None:
    raw = _sign(_valid_pairs())
    with pytest.raises(InvalidInitData, match="bad_signature"):
        verify_init_data(raw, bot_token="999999:wrong")


def test_expired_auth_date_rejected() -> None:
    raw = _sign(_valid_pairs(auth_date=1_600_000_000))
    with pytest.raises(InvalidInitData, match="expired"):
        verify_init_data(raw, bot_token=_BOT_TOKEN, now=1_600_000_000 + DEFAULT_MAX_AGE + 1)


def test_expiry_can_be_disabled() -> None:
    raw = _sign(_valid_pairs(auth_date=1_600_000_000))
    user = verify_init_data(raw, bot_token=_BOT_TOKEN, max_age_seconds=0, now=1_700_000_000)
    assert user.id == 42


def test_missing_user_rejected() -> None:
    pairs = [("auth_date", str(int(time.time()))), ("query_id", "x")]
    raw = _sign(pairs)
    with pytest.raises(InvalidInitData, match="missing_user"):
        verify_init_data(raw, bot_token=_BOT_TOKEN)


def test_user_without_id_rejected() -> None:
    pairs = [
        ("user", json.dumps({"first_name": "NoId"})),
        ("auth_date", str(int(time.time()))),
    ]
    raw = _sign(pairs)
    with pytest.raises(InvalidInitData, match="user_missing_id"):
        verify_init_data(raw, bot_token=_BOT_TOKEN)
