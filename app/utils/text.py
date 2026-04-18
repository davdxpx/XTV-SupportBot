from __future__ import annotations

import html
import re

_WHITESPACE = re.compile(r"\s+")


def escape_html(text: str | None) -> str:
    """Escape a user-supplied string for safe inclusion in a Telegram HTML message."""
    if not text:
        return ""
    return html.escape(text, quote=False)


def truncate(text: str, limit: int, suffix: str = "…") -> str:
    if len(text) <= limit:
        return text
    if limit <= len(suffix):
        return text[:limit]
    return text[: limit - len(suffix)] + suffix


def collapse_ws(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def user_mention(user_id: int, display: str) -> str:
    """Produce an HTML mention. ``display`` is escaped."""
    return f'<a href="tg://user?id={user_id}">{escape_html(display)}</a>'
