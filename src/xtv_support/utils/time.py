from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def humanize_delta(delta: timedelta) -> str:
    """Render a timedelta in compact form: '3d 4h', '12m', '42s'."""
    total_seconds = int(abs(delta).total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    if total_seconds < 3600:
        return f"{total_seconds // 60}m"
    if total_seconds < 86400:
        hours, rem = divmod(total_seconds, 3600)
        minutes = rem // 60
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    days, rem = divmod(total_seconds, 86400)
    hours = rem // 3600
    return f"{days}d {hours}h" if hours else f"{days}d"


def format_iso(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
