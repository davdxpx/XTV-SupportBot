from __future__ import annotations

from typing import Iterable


def wrap(body: str, *, expandable: bool = False) -> str:
    """Wrap text in a Telegram HTML <blockquote>. Caller is responsible for escaping content."""
    if expandable:
        return f"<blockquote expandable>{body}</blockquote>"
    return f"<blockquote>{body}</blockquote>"


def join_lines(lines: Iterable[str]) -> str:
    """Join lines with \\n, dropping any Nones."""
    return "\n".join(line for line in lines if line is not None)
