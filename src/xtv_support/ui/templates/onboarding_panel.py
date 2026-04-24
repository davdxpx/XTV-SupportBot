"""Onboarding panel — the ``/start`` / ``/home`` card + settings / FAQ cards.

All user-facing home-screen rendering lives here. Branding (name,
tagline, channel links) is driven by ``settings.BRAND_*`` so each
deploy can call itself whatever it wants without touching code.

Visual language matches the admin menu:
- ``━━━`` horizontal rules frame the card
- single-line hints render as ``<blockquote>``
- every button + title carries an emoji
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from xtv_support.ui.primitives.panel import Panel, PanelButton


@dataclass(frozen=True, slots=True)
class HomeStats:
    open_tickets: int = 0
    waiting_on_user: int = 0
    closed_this_month: int = 0


@dataclass(frozen=True, slots=True)
class BrandConfig:
    """Bundled branding strings pulled from :mod:`xtv_support.config.settings`."""

    name: str = "Support"
    tagline: str = "We're here to help."
    links: tuple[tuple[str, str], ...] = ()  # ((label, url), …)


def _brand_links_rows(brand: BrandConfig) -> tuple[tuple[PanelButton, ...], ...]:
    """Render the optional branding links as extra action rows."""
    buttons = [PanelButton(label=label, url=url) for label, url in brand.links if url]
    if not buttons:
        return ()
    rows: list[tuple[PanelButton, ...]] = []
    pair: list[PanelButton] = []
    for btn in buttons:
        pair.append(btn)
        if len(pair) == 2:
            rows.append(tuple(pair))
            pair = []
    if pair:
        rows.append(tuple(pair))
    return tuple(rows)


def onboarding_panel(
    *,
    user_first_name: str | None = None,
    unread_replies: int = 0,
    stats: HomeStats | None = None,
    announcement: str | None = None,
    brand: BrandConfig | None = None,
) -> Panel:
    brand = brand or BrandConfig()
    greeting = (
        f"Hey <b>{user_first_name}</b>, welcome back! 👋" if user_first_name else "Welcome 👋"
    )

    body: list[str] = [greeting, f"<i>{brand.tagline}</i>"]
    if stats is not None and (stats.open_tickets or stats.closed_this_month):
        body.append("")
        body.append(
            f"📊 <b>{stats.open_tickets}</b> open · "
            f"<b>{stats.closed_this_month}</b> closed this month"
        )

    hints: list[str] = []
    if announcement:
        hints.append(f"📣 <b>{announcement}</b>")
    else:
        hints.append("💡 Tap a button below to get started.")

    my_tickets_label = (
        f"🗂 My tickets ({unread_replies} new)" if unread_replies > 0 else "🗂 My tickets"
    )

    action_rows: tuple[tuple[PanelButton, ...], ...] = (
        (
            PanelButton(label="📮 New ticket", callback="cb:v2:home:new_ticket"),
            PanelButton(label="📚 Browse help", callback="cb:v2:home:faq"),
        ),
        (
            PanelButton(label=my_tickets_label, callback="cb:v2:home:my_tickets"),
            PanelButton(label="⚙️ Settings", callback="cb:v2:home:settings"),
        ),
    )
    action_rows = action_rows + _brand_links_rows(brand)

    return Panel(
        title=f"🤝 {brand.name}",
        body=tuple(body),
        hints=tuple(hints),
        action_rows=action_rows,
    )


def faq_browse_panel(
    *,
    query: str | None = None,
    articles: Iterable[tuple[str, str]] | None = None,
    page: int = 1,
    total_pages: int = 1,
    next_cb: str | None = None,
    prev_cb: str | None = None,
) -> Panel:
    body: list[str] = []
    article_list = list(articles or [])
    if query:
        body.append(f"<i>Results for</i> <b>{query}</b>")
        body.append("")
    if not article_list:
        body.append("<i>No matching articles found.</i>")
    else:
        for i, (title, preview) in enumerate(article_list, start=1):
            body.append(f"<b>{i}. {title}</b>")
            if preview:
                body.append(f"<i>{preview}</i>")
            body.append("")

    hints = ("🔍 Type a keyword after /faq to search — e.g. <code>/faq refund</code>.",)

    action_rows = (
        (PanelButton(label="🔍 Search", callback="cb:v2:faq:search"),),
        (PanelButton(label="◀ Home", callback="cb:v2:home:open"),),
    )
    return Panel(
        title="📚 Help center",
        body=tuple(body),
        hints=hints,
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
        f"🌐 <b>Language</b>: <code>{language}</code>",
    )
    hints = ("💾 Changes are saved instantly — no submit button needed.",)
    action_rows = (
        (PanelButton(label="🌐 Change language", callback="cb:v2:settings:lang"),),
        (
            PanelButton(
                label=f"{_check(notify_on_reply)} Notify on reply",
                callback="cb:v2:settings:toggle:notify_reply",
            ),
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
        hints=hints,
        action_rows=action_rows,
    )


LANGUAGE_NAMES: tuple[tuple[str, str], ...] = (
    ("en", "🇬🇧 English"),
    ("de", "🇩🇪 Deutsch"),
    ("es", "🇪🇸 Español"),
    ("ru", "🇷🇺 Русский"),
    ("hi", "🇮🇳 हिन्दी"),
    ("bn", "🇧🇩 বাংলা"),
    ("ta", "🇱🇰 தமிழ்"),
    ("te", "🇮🇳 తెలుగు"),
    ("mr", "🇮🇳 मराठी"),
    ("pa", "🇮🇳 ਪੰਜਾਬੀ"),
    ("gu", "🇮🇳 ગુજરાતી"),
    ("ur", "🇵🇰 اردو"),
)


def language_picker_panel(*, current_lang: str, supported: tuple[str, ...]) -> Panel:
    """Inline language picker — reachable from Settings → 🌐 Change language."""
    rows: list[tuple[PanelButton, ...]] = []
    pair: list[PanelButton] = []
    for code, label in LANGUAGE_NAMES:
        if code not in supported:
            continue
        marker = "✅" if code == current_lang else "·"
        pair.append(
            PanelButton(
                label=f"{marker} {label}",
                callback=f"cb:v2:settings:lang_pick:{code}",
            )
        )
        if len(pair) == 2:
            rows.append(tuple(pair))
            pair = []
    if pair:
        rows.append(tuple(pair))
    rows.append((PanelButton(label="◀ Back to settings", callback="cb:v2:home:settings"),))

    return Panel(
        title="🌐 Change language",
        subtitle=f"Current: {current_lang}",
        body=("Pick the language the bot should use when talking to you.",),
        hints=("🔁 Takes effect instantly for new messages.",),
        action_rows=tuple(rows),
    )


def project_picker_panel(
    *,
    projects: Iterable[dict],
    brand: BrandConfig | None = None,
) -> Panel:
    """Intake card shown when the user taps 📮 **New ticket**."""
    brand = brand or BrandConfig()
    project_list = list(projects)

    body: list[str] = ["Pick the area your question is about."]
    rows: list[tuple[PanelButton, ...]] = []
    pair: list[PanelButton] = []
    for proj in project_list:
        label = str(proj.get("name") or proj.get("slug") or "Project")
        pair.append(
            PanelButton(
                label=f"📂 {label}",
                callback=f"u:sp|{proj.get('_id') or proj.get('slug')}",
            )
        )
        if len(pair) == 2:
            rows.append(tuple(pair))
            pair = []
    if pair:
        rows.append(tuple(pair))

    rows.append((PanelButton(label="◀ Home", callback="cb:v2:home:open"),))

    hints = ("💡 After picking, just type your question — a photo or document works too.",)
    if not project_list:
        body = ["<i>No intake surfaces configured yet.</i>"]
        hints = (
            "⚙️ An admin needs to add a project before users can file tickets. "
            "They can do that from <code>/admin → 📁 Projects</code>.",
        )

    return Panel(
        title=f"📮 New ticket — {brand.name}",
        body=tuple(body),
        hints=hints,
        action_rows=tuple(rows),
    )


def ticket_intake_panel(
    *,
    project_name: str,
    project_description: str | None = None,
    brand: BrandConfig | None = None,
) -> Panel:
    """Card shown after a user picks a project but before they type."""
    brand = brand or BrandConfig()
    body: list[str] = [
        f"You're filing a ticket in <b>{project_name}</b>.",
        "",
        "Send your question as a text message — a photo, voice note or document is fine too.",
    ]
    if project_description:
        body.append("")
        body.append(f"<i>{project_description}</i>")

    hints = (
        "⏱ We usually reply within 30 minutes during business hours.",
        "💬 Keep typing — every message you send is added to the same ticket.",
    )

    action_rows = (
        (
            PanelButton(label="◀ Pick another project", callback="cb:v2:home:new_ticket"),
            PanelButton(label="❌ Cancel", callback="cb:v2:home:open"),
        ),
    )

    return Panel(
        title=f"📮 {brand.name} — new ticket",
        body=tuple(body),
        hints=hints,
        action_rows=action_rows,
    )
