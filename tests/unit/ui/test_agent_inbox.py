from __future__ import annotations

from xtv_support.ui.templates.agent_inbox import (
    SAVED_VIEWS,
    CustomerHistorySummary,
    InboxRow,
    render_customer_history,
    render_inbox,
)


def test_saved_views_exposed() -> None:
    keys = [k for k, _ in SAVED_VIEWS]
    assert "my_open" in keys
    assert "unassigned" in keys
    assert "overdue" in keys
    assert "high_priority" in keys


def test_render_inbox_empty_state() -> None:
    panel = render_inbox(active_view="my_open", rows=[], selected_count=0)
    text = panel.render_text()
    assert "Agent Inbox" in text
    assert "No tickets match" in text


def test_render_inbox_shows_ticket_rows_and_bulk_footer() -> None:
    rows = [
        InboxRow(
            ticket_id="t1",
            title="Login fails",
            priority="high",
            tags=("billing",),
            unassigned=True,
            sla_at_risk=True,
            selected=True,
        ),
        InboxRow(ticket_id="t2", title="Typo in welcome email", priority="low"),
    ]
    panel = render_inbox(active_view="unassigned", rows=rows, selected_count=1)
    text = panel.render_text()
    assert "1 selected" in text
    specs = panel._row_specs()
    # Row 0: tabs, rows 1-2: ticket rows, next: bulk actions row, then clear row
    labels = [c["label"] for r in specs for c in r]
    assert any("Login fails" in lbl for lbl in labels)
    assert any("Close" in lbl and "✅" in lbl for lbl in labels)
    assert any("Clear selection" in lbl for lbl in labels)


def test_render_inbox_pagination_when_needed() -> None:
    panel = render_inbox(
        active_view="my_open",
        rows=[InboxRow(ticket_id="t", title="x")],
        page=2,
        total_pages=5,
        selected_count=0,
    )
    text = panel.render_text()
    assert "Page 2/5" in text


def test_customer_history_renders_vip_flag_and_stats() -> None:
    out = render_customer_history(
        user_name="Ada",
        user_id=42,
        summary=CustomerHistorySummary(
            total_tickets=7,
            closed_tickets=6,
            csat_avg=4.8,
            avg_first_response_min=12,
            is_vip=True,
        ),
        recent=[("Refund issue", "closed"), ("Password reset", "open")],
    )
    assert "Ada" in out
    assert "ID 42" in out
    assert "VIP" in out
    assert "7 tickets" in out
    assert "4.8" in out
    assert "Refund issue" in out
