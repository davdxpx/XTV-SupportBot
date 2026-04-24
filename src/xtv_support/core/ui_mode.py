"""Dual-mode UI switch — Telegram chat inline buttons vs Mini-App.

Every handler that renders a panel asks :func:`should_use_webapp` (or the
simpler :func:`resolved_mode`) to decide which keyboard variant to send.
The decision order is::

    1. ``users.ui_pref`` on the user doc — explicit per-user override
    2. ``UI_MODE`` env var — global default
    3. ``chat`` — safe fallback if neither is set

``UI_MODE=hybrid`` means render both: callback-data rows AND a WebApp
tile, so users can pick in-flight. The same enum is used by the FastAPI
auth layer to decide whether ``initData`` is accepted.
"""

from __future__ import annotations

from enum import StrEnum


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
