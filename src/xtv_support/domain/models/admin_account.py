"""Admin web-console account.

A real person who logs into the admin SPA with a username + password,
created via the one-time "Register with API Key" ceremony. The account
only *authenticates* a caller; *authorization* is read from the existing
Role/Team system, keyed by :attr:`telegram_user_id`.

Usernames are stored lowercase (:attr:`username`) for case-insensitive
uniqueness and login; the originally-typed casing is preserved in
:attr:`display_username` for rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AdminAccount:
    id: str
    username: str
    display_username: str
    first_name: str
    last_name: str | None
    password_hash: str
    telegram_user_id: int
    created_at: datetime
    created_via_key_id: str
    last_login_at: datetime | None = None
    disabled_at: datetime | None = None


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
