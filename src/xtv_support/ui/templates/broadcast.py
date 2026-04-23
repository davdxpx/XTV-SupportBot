from __future__ import annotations

from app.constants import CallbackPrefix, MAX_BROADCAST_LEN
from app.ui.card import Card, ProgressCard
from app.ui.keyboards import btn, rows
from app.utils.text import escape_html, truncate


def prompt() -> Card:
    return Card(
        title="📢 Broadcast",
        body=[
            "Send the message you want to broadcast to all active users.",
            "<i>Plain text only — no media in v1.</i>",
            f"Max <b>{MAX_BROADCAST_LEN}</b> characters.",
        ],
        footer="<i>/cancel to abort.</i>",
    )


def preview(text: str, total: int) -> Card:
    buttons = rows(
        [
            btn("▶️ Start", CallbackPrefix.ADMIN_BROADCAST_CONFIRM),
            btn("❌ Cancel", CallbackPrefix.ADMIN_BROADCAST_CANCEL),
        ],
    )
    return Card(
        title="📢 Broadcast • preview",
        body=[f"Target: <b>{total}</b> active users."],
        quote=truncate(escape_html(text), 600),
        quote_expandable=True,
        footer="<i>Start to begin sending, Cancel to discard.</i>",
        buttons=buttons,
    )


def _progress_card(
    *,
    status: str,
    text: str,
    sent: int,
    failed: int,
    blocked: int,
    total: int,
    paused: bool = False,
) -> ProgressCard:
    pct = sent / total if total else 0
    controls = rows(
        [
            btn(
                "▶️ Resume" if paused else "⏸ Pause",
                CallbackPrefix.ADMIN_BROADCAST_RESUME if paused else CallbackPrefix.ADMIN_BROADCAST_PAUSE,
            ),
            btn("❌ Cancel", CallbackPrefix.ADMIN_BROADCAST_CANCEL),
        ],
    )
    card = ProgressCard(
        title=f"📢 Broadcast • {status}",
        body=[
            f"Sent <b>{sent}</b>/{total}  •  failed <b>{failed}</b>  •  blocked <b>{blocked}</b>",
        ],
        quote=truncate(escape_html(text), 400),
        quote_expandable=True,
        buttons=controls,
    )
    card.progress = pct
    return card


def running(text: str, *, sent: int, failed: int, blocked: int, total: int) -> ProgressCard:
    return _progress_card(
        status="running",
        text=text, sent=sent, failed=failed, blocked=blocked, total=total, paused=False,
    )


def paused(text: str, *, sent: int, failed: int, blocked: int, total: int) -> ProgressCard:
    return _progress_card(
        status="paused",
        text=text, sent=sent, failed=failed, blocked=blocked, total=total, paused=True,
    )


def finished(
    text: str, *, sent: int, failed: int, blocked: int, total: int, cancelled: bool = False
) -> ProgressCard:
    state = "cancelled" if cancelled else "done"
    card = _progress_card(
        status=state,
        text=text, sent=sent, failed=failed, blocked=blocked, total=total, paused=False,
    )
    card.buttons = None
    card.progress = 1.0 if not cancelled else (sent / total if total else 0)
    return card


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
