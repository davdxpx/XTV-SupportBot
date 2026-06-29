"""Telegram WebApp ``initData`` verification.

When the user opens the bundled SPA via a Telegram Mini-App button,
the browser receives a signed query string called ``initData``. The
signature is an HMAC-SHA256 of the sorted key/value pairs using a
secret derived from the bot token — so any request carrying a valid
``initData`` came from Telegram itself, authenticated against the
correct bot.

The SPA forwards ``initData`` as an HTTP header:

    X-Telegram-Init-Data: user=%7B...%7D&auth_date=1724420000&hash=...

We validate the signature against ``BOT_TOKEN`` and reject anything
older than ``max_age_seconds`` (default one day) to limit replay.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from fastapi import Request

from xtv_support.core.logger import get_logger

_log = get_logger("api.auth_webapp")

INIT_DATA_HEADER = "X-Telegram-Init-Data"
DEFAULT_MAX_AGE = 24 * 60 * 60  # 1 day


@dataclass(frozen=True, slots=True)
class TelegramUser:
    """Decoded Telegram user from ``initData.user``.

    Only the fields we actually use elsewhere are exposed — the full
    Telegram user object has more (``photo_url``, ``is_premium``,
    ``allows_write_to_pm``) that we can add on demand.
    """

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_bot: bool = False
    auth_date: int = 0


class InvalidInitData(Exception):
    """Raised when ``initData`` fails signature or freshness checks."""


def _secret_key(bot_token: str) -> bytes:
    """Derive the WebApp HMAC key from the bot token.

    Telegram's scheme: ``secret = HMAC_SHA256(key="WebAppData", msg=bot_token)``.
    """
    return hmac.new(key=b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256).digest()


def _data_check_string(pairs: list[tuple[str, str]]) -> str:
    """Build the canonical check string: ``key=value\\n...`` sorted by key."""
    filtered = [(k, v) for k, v in pairs if k != "hash"]
    filtered.sort(key=lambda kv: kv[0])
    return "\n".join(f"{k}={v}" for k, v in filtered)


def verify_init_data(
    init_data: str,
    *,
    bot_token: str,
    max_age_seconds: int = DEFAULT_MAX_AGE,
    now: int | None = None,
) -> TelegramUser:
    """Validate ``initData`` and return the decoded :class:`TelegramUser`.

    Raises :class:`InvalidInitData` on any failure — malformed input,
    bad signature, or expired ``auth_date``.
    """
    if not init_data:
        raise InvalidInitData("empty_init_data")
    pairs = parse_qsl(init_data, strict_parsing=False, keep_blank_values=True)
    if not pairs:
        raise InvalidInitData("unparseable_init_data")
    data = dict(pairs)
    provided_hash = data.get("hash")
    if not provided_hash:
        raise InvalidInitData("missing_hash")

    check_string = _data_check_string(pairs)
    key = _secret_key(bot_token)
    computed = hmac.new(key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, provided_hash):
        raise InvalidInitData("bad_signature")

    try:
        auth_date = int(data.get("auth_date", "0"))
    except ValueError as exc:
        raise InvalidInitData("bad_auth_date") from exc

    current = int(now if now is not None else time.time())
    if max_age_seconds > 0 and current - auth_date > max_age_seconds:
        raise InvalidInitData("expired")

    user_raw = data.get("user")
    if not user_raw:
        raise InvalidInitData("missing_user")
    try:
        user_dict = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InvalidInitData("bad_user_json") from exc
    if not isinstance(user_dict, dict) or "id" not in user_dict:
        raise InvalidInitData("user_missing_id")

    return TelegramUser(
        id=int(user_dict["id"]),
        first_name=str(user_dict.get("first_name") or ""),
        last_name=user_dict.get("last_name"),
        username=user_dict.get("username"),
        language_code=user_dict.get("language_code"),
        is_bot=bool(user_dict.get("is_bot", False)),
        auth_date=auth_date,
    )


# ----------------------------------------------------------------------
# FastAPI dependency
# ----------------------------------------------------------------------
async def current_tg_user(request: Request) -> TelegramUser:
    """Resolve the Telegram user from the ``X-Telegram-Init-Data`` header.

    Raises 401 if the header is missing or the signature fails.
    """
    from fastapi import HTTPException

    from xtv_support.config.settings import settings

    raw = request.headers.get(INIT_DATA_HEADER)
    if not raw:
        raise HTTPException(status_code=401, detail="missing_init_data")
    bot_token = settings.BOT_TOKEN.get_secret_value()
    try:
        return verify_init_data(raw, bot_token=bot_token)
    except InvalidInitData as exc:
        _log.info("api.webapp_auth_rejected", reason=str(exc))
        raise HTTPException(status_code=401, detail=f"invalid_init_data:{exc}") from exc
