from __future__ import annotations

from app.core.callback_data import (
    CbAssignPick,
    CbPriorityPick,
    CbRate,
    CbTagToggle,
    CbTicket,
    starts_with,
)
from app.utils.ids import safe_objectid, short_ticket_id
from app.utils.text import collapse_ws, escape_html, truncate, user_mention
from app.utils.time import humanize_delta


def test_safe_objectid_valid():
    from bson import ObjectId

    oid = ObjectId()
    assert safe_objectid(str(oid)) == oid


def test_safe_objectid_invalid():
    assert safe_objectid("not-a-hex") is None
    assert safe_objectid("") is None
    assert safe_objectid(None) is None


def test_short_ticket_id():
    assert len(short_ticket_id("a" * 24)) == 6


def test_escape_html():
    assert escape_html("<b>hi</b>") == "&lt;b&gt;hi&lt;/b&gt;"
    assert escape_html(None) == ""


def test_truncate():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 7) == "hello \u2026"
    assert truncate("abc", 1) == "a"


def test_collapse_ws():
    assert collapse_ws("  hello   world ") == "hello world"


def test_user_mention_escapes():
    html = user_mention(42, "<danger>")
    assert 'href="tg://user?id=42"' in html
    assert "&lt;danger&gt;" in html


def test_humanize_delta_seconds():
    from datetime import timedelta

    assert humanize_delta(timedelta(seconds=12)) == "12s"
    assert humanize_delta(timedelta(minutes=3)) == "3m"
    assert humanize_delta(timedelta(hours=2, minutes=30)) == "2h 30m"
    assert humanize_delta(timedelta(days=1, hours=4)) == "1d 4h"


def test_callback_rate_roundtrip():
    original = CbRate(project_id="deadbeef", score=4)
    data = original.pack()
    assert data.startswith("u:rate|")
    restored = CbRate.unpack(data)
    assert restored.score == 4
    assert restored.project_id == "deadbeef"


def test_callback_assign_roundtrip():
    original = CbAssignPick(ticket_id="ab12", admin_id=999)
    data = original.pack()
    restored = CbAssignPick.unpack(data)
    assert restored.admin_id == 999
    assert restored.ticket_id == "ab12"


def test_callback_tag_toggle_roundtrip():
    original = CbTagToggle(ticket_id="tid", tag="bug")
    data = original.pack()
    restored = CbTagToggle.unpack(data)
    assert restored.tag == "bug"


def test_callback_priority_roundtrip():
    original = CbPriorityPick(ticket_id="tid", priority="high")
    data = original.pack()
    restored = CbPriorityPick.unpack(data)
    assert restored.priority == "high"


def test_starts_with_matches():
    import re

    pattern = starts_with("a:projects")
    assert re.match(pattern, "a:projects")
    assert re.match(pattern, "a:projects|some-id")
    assert not re.match(pattern, "a:projectslong")
