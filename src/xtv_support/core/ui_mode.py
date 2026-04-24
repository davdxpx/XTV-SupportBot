"""Dual-mode UI switch — Telegram chat inline buttons vs Mini-App.

Every handler that renders a panel asks :func:`resolve_mode_for_user`
(async, hits Mongo once for the user's ``ui_pref``) to decide which
keyboard variant to send. Phase 4 adds per-user override +
graceful-fallback logic to the enum shipped in Phase 1.

Decision order::

    1. ``users.ui_pref`` on the caller's doc — explicit per-user pref
    2. ``UI_MODE`` env var — global default
    3. chat — safe fallback if neither is set

Even when the resolved mode is ``webapp`` or ``hybrid``, the actual
render still needs a valid ``WEBAPP_URL``. If it's empty we downgrade
to ``chat`` silently so a misconfigured deploy doesn't emit broken
keyboards.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type-only
    from motor.motor_asyncio import AsyncIOMotorDatabase


class UIMode(StrEnum):
    CHAT = "chat"
    WEBAPP = "webapp"
    HYBRID = "hybrid"

    @classmethod
    def parse(cls, value: str | None) -> UIMode:
        """Tolerant parser — unknown values fall back to CHAT.

        Using this instead of raw ``UIMode(value)`` means a typo in env
        config degrades gracefully to the safe default instead of
        crashing the bot at boot.
        """
        if not value:
            return cls.CHAT
        token = value.strip().lower()
        for member in cls:
            if member.value == token:
                return member
        return cls.CHAT


def resolved_mode(
    *,
    global_mode: UIMode | str | None,
    user_pref: str | None = None,
) -> UIMode:
    """Return the effective mode for a given user.

    User preference wins, then the global default. ``user_pref=None``
    means "no opinion" — the global default applies.
    """
    if user_pref:
        return UIMode.parse(user_pref)
    if isinstance(global_mode, UIMode):
        return global_mode
    return UIMode.parse(global_mode)


def should_use_webapp(mode: UIMode) -> bool:
    """True when the handler should render a WebApp button."""
    return mode in (UIMode.WEBAPP, UIMode.HYBRID)


def should_render_callbacks(mode: UIMode) -> bool:
    """True when the handler should also render classic callback buttons.

    In hybrid mode both are rendered; in pure-webapp mode the callback
    path is suppressed so the bot UI reduces to a single Open-App tile.
    """
    return mode in (UIMode.CHAT, UIMode.HYBRID)


# ----------------------------------------------------------------------
# Graceful fallback
# ----------------------------------------------------------------------
# Telegram Mini-Apps require client ≥ 6.0 (released April 2022). Below
# that, the inline ``web_app`` button just doesn't render. We detect
# via the pyrogram ``User.client_version`` attribute when available;
# absence is treated as "recent enough" to avoid gating modern clients
# on missing metadata.
MIN_WEBAPP_CLIENT_VERSION = (6, 0)


def _parse_version(raw: str | None) -> tuple[int, ...]:
    if not raw:
        return ()
    out: list[int] = []
    for part in raw.split("."):
        digits = "".join(c for c in part if c.isdigit())
        if not digits:
            break
        out.append(int(digits))
    return tuple(out)


def client_supports_webapp(client_version: str | None) -> bool:
    """Return True if the given Telegram client string looks WebApp-capable.

    Missing / unparseable versions default to ``True`` — we'd rather
    let a modern client through than gate it on missing metadata.
    The downgrade is strictly defensive: old clients + WebApp button
    render a silent no-op.
    """
    parsed = _parse_version(client_version)
    if not parsed:
        return True
    for required, actual in zip(MIN_WEBAPP_CLIENT_VERSION, parsed, strict=False):
        if actual > required:
            return True
        if actual < required:
            return False
    return True


async def resolve_mode_for_user(
    db: AsyncIOMotorDatabase,
    *,
    user_id: int,
    global_mode: UIMode | str | None,
    webapp_url: str | None,
    client_version: str | None = None,
) -> UIMode:
    """Full resolution pipeline for a single handler render.

    Pulls the user's ``ui_pref`` from Mongo (best-effort; missing doc
    or error falls through to the global default), then applies the
    two defensive downgrades:

    * ``WEBAPP_URL`` empty → force chat
    * Old Telegram client → force chat
    """
    user_pref: str | None = None
    try:
        doc = await db.users.find_one({"user_id": user_id}, projection={"ui_pref": 1})
        if doc:
            user_pref = doc.get("ui_pref")
    except Exception:  # noqa: BLE001 — Mongo hiccups shouldn't break rendering
        user_pref = None

    mode = resolved_mode(global_mode=global_mode, user_pref=user_pref)

    if should_use_webapp(mode):
        if not (webapp_url and webapp_url.startswith("https://")):
            return UIMode.CHAT
        if not client_supports_webapp(client_version):
            return UIMode.CHAT

    return mode
