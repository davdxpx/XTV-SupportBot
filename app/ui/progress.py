from __future__ import annotations

from app.constants import DEFAULT_PROGRESS_WIDTH
from app.ui.glyphs import EMPTY, FILL


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def bar(pct: float, width: int = DEFAULT_PROGRESS_WIDTH, *, fill: str = FILL, empty: str = EMPTY) -> str:
    """Render an ASCII progress bar. pct is in [0, 1]."""
    pct = clamp(pct)
    filled = int(round(pct * width))
    filled = max(0, min(width, filled))
    return f"[{fill * filled}{empty * (width - filled)}]"


def percentage(pct: float) -> str:
    """Format a 0..1 value as 'XX.X%'."""
    return f"{clamp(pct) * 100:.1f}%"
