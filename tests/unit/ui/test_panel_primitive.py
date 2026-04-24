from __future__ import annotations

from xtv_support.ui.primitives.panel import HR_RULE, Panel, PanelButton, StatTile, Tab


def test_panel_renders_title_with_hr_by_default() -> None:
    p = Panel(title="Hello")
    text = p.render_text()
    assert text.startswith("<b>Hello</b>")
    # Default ``hr=True`` wraps the card with HR rules.
    assert HR_RULE in text
    assert p._row_specs() == []


def test_panel_hr_can_be_disabled() -> None:
    p = Panel(title="Hello", hr=False)
    text = p.render_text()
    assert text == "<b>Hello</b>"


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


def test_panel_tabs_wrap_at_tabs_per_row() -> None:
    # 8 tabs with default tabs_per_row=4 → two keyboard rows of 4.
    p = Panel(
        title="Admin",
        tabs=tuple(
            Tab(key=str(i), label=f"T{i}", callback=f"cb:v2:admin:tab:{i}") for i in range(8)
        ),
    )
    rows = p._row_specs()
    assert len(rows[0]) == 4
    assert len(rows[1]) == 4


def test_panel_tabs_respect_custom_per_row() -> None:
    p = Panel(
        title="Admin",
        tabs_per_row=3,
        tabs=tuple(
            Tab(key=str(i), label=f"T{i}", callback=f"cb:v2:admin:tab:{i}") for i in range(7)
        ),
    )
    rows = p._row_specs()
    assert [len(r) for r in rows[:3]] == [3, 3, 1]


def test_panel_hints_render_as_blockquote() -> None:
    p = Panel(
        title="Admin",
        hints=("💡 This is a one-line tip.",),
    )
    text = p.render_text()
    assert "<blockquote>💡 This is a one-line tip.</blockquote>" in text


def test_panel_multiple_hints_stack() -> None:
    p = Panel(
        title="Admin",
        hints=("first hint", "second hint"),
    )
    text = p.render_text()
    assert text.count("<blockquote>") == 2


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
    assert len(rows) == 2
    assert rows[0][0]["label"] == "Close all"
    assert rows[1][0]["label"] == "Next ▶"
