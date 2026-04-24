from __future__ import annotations

from collections.abc import Iterable


def wrap(body: str, *, expandable: bool = False) -> str:
    """Wrap text in a Telegram HTML <blockquote>. Caller is responsible for escaping content."""
    if expandable:
        return f"<blockquote expandable>{body}</blockquote>"
    return f"<blockquote>{body}</blockquote>"


def join_lines(lines: Iterable[str]) -> str:
    """Join lines with \\n, dropping any Nones."""
    return "\n".join(line for line in lines if line is not None)


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
