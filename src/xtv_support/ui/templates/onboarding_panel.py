"""Onboarding panel — the new ``/start`` / ``/home`` card.

Four primary buttons:

    📮 New ticket    📚 Browse help
    🗂 My tickets    ⚙️ Settings

The unread-reply badge on *My tickets* is baked into the label when
``unread > 0``. The language is auto-detected from the Telegram
``language_code`` the first time a user interacts with the bot; the
user can flip it in Settings.
"""

from __future__ import annotations

from dataclasses import dataclass

from xtv_support.ui.primitives.panel import Panel, PanelButton


@dataclass(frozen=True, slots=True)
class HomeStats:
    open_tickets: int = 0
    waiting_on_user: int = 0
    closed_this_month: int = 0


def onboarding_panel(
    *,
    user_first_name: str | None = None,
    unread_replies: int = 0,
    stats: HomeStats | None = None,
    announcement: str | None = None,
    channel_url: str | None = None,
) -> Panel:
    greeting = (
        f"Hey {user_first_name}, welcome back! 👋" if user_first_name else "Welcome 👋"
    )

    body: list[str] = [greeting]
    if stats is not None and (stats.open_tickets or stats.closed_this_month):
        body.append(
            f"<i>{stats.open_tickets} open · {stats.closed_this_month} closed this month</i>"
        )
    if announcement:
        body.append("")
        body.append(f"📣 <b>{announcement}</b>")

    my_tickets_label = (
        f"🗂 My tickets ({unread_replies} new)" if unread_replies > 0 else "🗂 My tickets"
    )

    action_rows = (
        (
            PanelButton(label="📮 New ticket", callback="cb:v2:home:new_ticket"),
            PanelButton(label="📚 Browse help", callback="cb:v2:home:faq"),
        ),
        (
            PanelButton(label=my_tickets_label, callback="cb:v2:home:my_tickets"),
            PanelButton(label="⚙️ Settings", callback="cb:v2:home:settings"),
        ),
    )

    extra_rows = ()
    if channel_url:
        extra_rows = (
            (PanelButton(label="XTV Network", url=channel_url),),
        )

    return Panel(
        title="XTV Support",
        subtitle=None,
        body=tuple(body),
        action_rows=action_rows + extra_rows,
        footer="<i>Tap a button to get started.</i>",
    )


def faq_browse_panel(
    *,
    query: str | None = None,
    articles: list[tuple[str, str]] | None = None,
    page: int = 1,
    total_pages: int = 1,
    next_cb: str | None = None,
    prev_cb: str | None = None,
) -> Panel:
    body: list[str] = []
    if query:
        body.append(f"<i>Results for</i>  <b>{query}</b>")
    if not articles:
        body.append("<i>No matching articles found.</i>")
    else:
        for i, (title, preview) in enumerate(articles, start=1):
            body.append(f"<b>{i}. {title}</b>")
            if preview:
                body.append(f"<i>{preview}</i>")
            body.append("")

    action_rows = (
        (PanelButton(label="🔍 Search", callback="cb:v2:faq:search"),),
        (PanelButton(label="◀ Home", callback="cb:v2:home:open"),),
    )
    return Panel(
        title="📚 Help Center",
        body=tuple(body),
        action_rows=action_rows,
        page=page,
        total_pages=total_pages,
        page_prev_cb=prev_cb,
        page_next_cb=next_cb,
    )


def settings_panel(
    *,
    language: str = "en",
    notify_on_reply: bool = True,
    notify_csat: bool = True,
    notify_announcements: bool = True,
) -> Panel:
    def _check(on: bool) -> str:
        return "✅" if on else "⬜"

    body = (
        "Control how the bot talks to you.",
        "",
        f"🌐  <b>Language</b>: {language}",
    )
    action_rows = (
        (PanelButton(label="🌐 Change language", callback="cb:v2:settings:lang"),),
        (
            PanelButton(
                label=f"{_check(notify_on_reply)} Notify on reply",
                callback="cb:v2:settings:toggle:notify_reply",
            ),
        ),
        (
            PanelButton(
                label=f"{_check(notify_csat)} CSAT after close",
                callback="cb:v2:settings:toggle:notify_csat",
            ),
        ),
        (
            PanelButton(
                label=f"{_check(notify_announcements)} Announcements",
                callback="cb:v2:settings:toggle:notify_announcements",
            ),
        ),
        (
            PanelButton(label="📥 Export my data", callback="cb:v2:settings:gdpr_export"),
            PanelButton(label="🗑 Delete my data", callback="cb:v2:settings:gdpr_delete"),
        ),
        (PanelButton(label="◀ Home", callback="cb:v2:home:open"),),
    )
    return Panel(
        title="⚙️ Settings",
        body=body,
        action_rows=action_rows,
    )
