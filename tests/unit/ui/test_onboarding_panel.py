from __future__ import annotations

from xtv_support.ui.templates.onboarding_panel import (
    HomeStats,
    faq_browse_panel,
    onboarding_panel,
    settings_panel,
)


def test_onboarding_panel_greets_by_name() -> None:
    panel = onboarding_panel(user_first_name="Luca", unread_replies=3)
    text = panel.render_text()
    assert "Luca" in text
    rows = panel._row_specs()
    # Row 0: action buttons (New ticket / Browse help)
    assert any("New ticket" in c["label"] for r in rows for c in r)
    # My tickets row shows unread badge
    assert any("(3 new)" in c["label"] for r in rows for c in r)


def test_onboarding_panel_without_user_name() -> None:
    panel = onboarding_panel()
    text = panel.render_text()
    assert "Welcome" in text


def test_onboarding_panel_stats_rendered() -> None:
    panel = onboarding_panel(stats=HomeStats(open_tickets=2, closed_this_month=7))
    text = panel.render_text()
    assert "2 open" in text
    assert "7 closed" in text


def test_onboarding_panel_announcement_strip() -> None:
    panel = onboarding_panel(announcement="Maintenance Sun 02:00 UTC")
    text = panel.render_text()
    assert "Maintenance" in text


def test_faq_browse_panel_renders_articles() -> None:
    panel = faq_browse_panel(
        query="refund",
        articles=[("Refund policy", "We refund within 14 days.")],
    )
    text = panel.render_text()
    assert "refund" in text
    assert "Refund policy" in text


def test_faq_browse_panel_empty_state() -> None:
    panel = faq_browse_panel(query="asdzxc", articles=[])
    text = panel.render_text()
    assert "No matching" in text


def test_settings_panel_reflects_toggles() -> None:
    panel = settings_panel(
        language="de",
        notify_on_reply=False,
        notify_csat=True,
        notify_announcements=True,
    )
    text = panel.render_text()
    assert "de" in text
    rows = panel._row_specs()
    labels = [c["label"] for r in rows for c in r]
    assert any("⬜ Notify on reply" in lbl for lbl in labels)
    assert any("✅ CSAT after close" in lbl for lbl in labels)
