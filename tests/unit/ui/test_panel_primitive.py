from __future__ import annotations

from xtv_support.ui.primitives.panel import Panel, PanelButton, StatTile, Tab


def test_panel_renders_title_only() -> None:
    p = Panel(title="Hello")
    text = p.render_text()
    assert text == "<b>Hello</b>"
    assert p._row_specs() == []


def test_panel_renders_tabs_and_stats() -> None:
    p = Panel(
        title="Admin",
        tabs=(Tab(key="o", label="Overview", callback="cb:v2:admin:tab:o", active=True),),
        stats=(StatTile(label="Open tickets", value="42"),),
    )
    text = p.render_text()
    assert "<b>Admin</b>" in text
    assert "Overview" in text
    assert "Open tickets" in text
    rows = p._row_specs()
    assert rows and rows[0][0]["callback"] == "cb:v2:admin:tab:o"


def test_panel_action_rows_and_pagination() -> None:
    p = Panel(
        title="Inbox",
        action_rows=((PanelButton(label="Close all", callback="cb:v2:inbox:close"),),),
        page=1,
        total_pages=3,
        page_next_cb="cb:v2:inbox:next",
    )
    text = p.render_text()
    assert "Page 1/3" in text
    rows = p._row_specs()
    # One action row + one pagination nav row
    assert len(rows) == 2
    assert rows[0][0]["label"] == "Close all"
    assert rows[1][0]["label"] == "Next ▶"
