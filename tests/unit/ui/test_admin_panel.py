from __future__ import annotations

from xtv_support.ui.templates.admin_panel import (
    OverviewStats,
    TABS,
    render_analytics_tab,
    render_broadcasts_tab,
    render_overview,
    render_projects_tab,
    render_rules_tab,
    render_settings_tab,
    render_teams_tab,
    render_tickets_tab,
)


def test_tabs_cover_all_eight_sections() -> None:
    keys = [k for k, _ in TABS]
    assert keys == [
        "overview",
        "tickets",
        "teams",
        "projects",
        "rules",
        "broadcasts",
        "analytics",
        "settings",
    ]


def test_overview_renders_stat_tiles() -> None:
    stats = OverviewStats(open_tickets=5, sla_at_risk=1, unassigned=2, active_agents=3)
    panel = render_overview(stats)
    text = panel.render_text()
    assert "Admin Control Panel" in text
    assert "Overview" in text
    assert "5" in text and "Open tickets" in text
    # tabs row should highlight "Overview"
    rows = panel._row_specs()
    assert rows  # tabs row + action row


def test_each_tab_builder_returns_a_panel() -> None:
    stats = OverviewStats()
    for builder in (
        lambda: render_overview(stats),
        lambda: render_tickets_tab(3, 4),
        lambda: render_teams_tab(2, 10),
        lambda: render_projects_tab(5),
        lambda: render_rules_tab(0, 0),
        lambda: render_broadcasts_tab(),
        lambda: render_analytics_tab(7, 42, 0.95),
        lambda: render_settings_tab([("NEW_ONBOARDING", False), ("CSAT", True)]),
    ):
        panel = builder()
        assert panel.render_text().startswith("<b>⚙️ Admin Control Panel</b>")


def test_analytics_tab_shows_compliance_percentage() -> None:
    panel = render_analytics_tab(7, 100, 0.933)
    text = panel.render_text()
    assert "93.3%" in text


def test_settings_tab_uses_checkboxes() -> None:
    panel = render_settings_tab([("NEW_ONBOARDING", True), ("CSAT", False)])
    rows = panel._row_specs()
    labels = [c["label"] for r in rows for c in r]
    assert any("✅ NEW_ONBOARDING" in lbl for lbl in labels)
    assert any("⬜ CSAT" in lbl for lbl in labels)
