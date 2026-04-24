from __future__ import annotations

from xtv_support.ui.templates.admin_panel import (
    SECTIONS,
    OverviewStats,
    render_analytics_section,
    render_broadcasts_section,
    render_home,
    render_overview_section,
    render_projects_section,
    render_rules_section,
    render_settings_section,
    render_teams_section,
    render_tickets_section,
)


def test_sections_cover_all_eight() -> None:
    keys = [k for k, _ in SECTIONS]
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


def test_home_renders_2_per_row_grid() -> None:
    stats = OverviewStats(open_tickets=5, sla_at_risk=1, unassigned=2, active_agents=3)
    panel = render_home(stats)
    rows = panel._row_specs()
    # Eight sections laid out as four rows of two drill-down tiles each.
    assert len(rows) == 4
    for row in rows:
        assert len(row) == 2
    # Tile callbacks land on the new ``section:<key>`` routes.
    first_cb = rows[0][0]["callback"]
    assert first_cb.startswith("cb:v2:admin:section:")


def test_home_emojis_present_in_tile_labels() -> None:
    panel = render_home(OverviewStats())
    labels = [c["label"] for r in panel._row_specs() for c in r]
    # Every section tile starts with an emoji glyph (non-ASCII first char).
    for label in labels:
        assert ord(label[0]) > 127, f"expected emoji prefix, got {label!r}"


def test_overview_section_renders_stat_tiles() -> None:
    stats = OverviewStats(open_tickets=5, sla_at_risk=1, unassigned=2, active_agents=3)
    panel = render_overview_section(stats)
    text = panel.render_text()
    assert "Overview" in text
    assert "5" in text and "Open tickets" in text


def test_each_section_builder_returns_a_framed_panel() -> None:
    stats = OverviewStats()
    for builder in (
        lambda: render_home(stats),
        lambda: render_overview_section(stats),
        lambda: render_tickets_section(3, 4),
        lambda: render_teams_section(2, 10),
        lambda: render_projects_section(5),
        lambda: render_rules_section(0, 0),
        lambda: render_broadcasts_section(),
        lambda: render_analytics_section(7, 42, 0.95),
        lambda: render_settings_section([("CSAT", True), ("KB_GATE", False)]),
    ):
        panel = builder()
        text = panel.render_text()
        # Every admin card is framed by the HR rule.
        assert "━" in text


def test_analytics_section_shows_compliance_percentage() -> None:
    panel = render_analytics_section(7, 100, 0.933)
    text = panel.render_text()
    assert "93.3%" in text


def test_settings_section_uses_checkboxes() -> None:
    panel = render_settings_section([("AI_DRAFTS", True), ("CSAT", False)])
    rows = panel._row_specs()
    labels = [c["label"] for r in rows for c in r]
    assert any("✅ AI_DRAFTS" in lbl for lbl in labels)
    assert any("⬜ CSAT" in lbl for lbl in labels)


def test_section_pages_carry_admin_home_back_button() -> None:
    # Every section (except ``home`` itself) should include a ``◀ Admin
    # home`` button pointing at the drill-down root.
    for builder in (
        lambda: render_overview_section(OverviewStats()),
        lambda: render_tickets_section(0, 0),
        lambda: render_teams_section(0, 0),
        lambda: render_projects_section(0),
        lambda: render_rules_section(0, 0),
        lambda: render_broadcasts_section(),
        lambda: render_analytics_section(7, 0, 1.0),
        lambda: render_settings_section([]),
    ):
        panel = builder()
        flat = [c for r in panel._row_specs() for c in r]
        back = [c for c in flat if "Admin home" in c["label"]]
        assert back, f"missing ◀ Admin home button on {builder.__name__}"
        assert back[0]["callback"] == "cb:v2:admin:section:home"
