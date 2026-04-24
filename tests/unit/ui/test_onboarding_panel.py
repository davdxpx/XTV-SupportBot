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
    # The stat line now wraps the numbers in <b>…</b> and the phrase
    # "open" / "closed this month" — match both pieces without being
    # sensitive to inner HTML.
    assert "<b>2</b> open" in text
    assert "<b>7</b>" in text and "closed this month" in text


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


def test_onboarding_panel_hybrid_keeps_callbacks_and_adds_webapp_row() -> None:
    panel = onboarding_panel(webapp_url="https://xtvsupport.up.railway.app/")
    rows = panel._row_specs()
    labels = [c["label"] for r in rows for c in r]
    assert any("New ticket" in lbl for lbl in labels)
    assert any("Open in app" in lbl for lbl in labels)
    webapp_cells = [c for r in rows for c in r if c.get("webapp_url")]
    assert webapp_cells and webapp_cells[0]["webapp_url"].startswith("https://")


def test_onboarding_panel_webapp_only_hides_callbacks() -> None:
    panel = onboarding_panel(
        webapp_url="https://xtvsupport.up.railway.app/",
        webapp_only=True,
    )
    rows = panel._row_specs()
    callbacks = [c for r in rows for c in r if c.get("callback")]
    assert not callbacks
    webapp_cells = [c for r in rows for c in r if c.get("webapp_url")]
    assert len(webapp_cells) == 1


def test_onboarding_panel_ignores_non_https_webapp_url() -> None:
    panel = onboarding_panel(webapp_url="http://insecure.example/")
    rows = panel._row_specs()
    assert not [c for r in rows for c in r if c.get("webapp_url")]


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
