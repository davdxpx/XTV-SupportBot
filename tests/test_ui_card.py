from __future__ import annotations

from xtv_support.ui.primitives.card import Card
from xtv_support.ui.primitives.progress import bar, percentage


def test_progress_bar_full():
    assert bar(1.0, width=4) == "[\u25a0\u25a0\u25a0\u25a0]"


def test_progress_bar_empty():
    assert bar(0.0, width=4) == "[\u25a1\u25a1\u25a1\u25a1]"


def test_progress_bar_partial():
    out = bar(0.5, width=4)
    assert out.startswith("[") and out.endswith("]")
    assert out.count("\u25a0") == 2
    assert out.count("\u25a1") == 2


def test_percentage():
    assert percentage(0.479) == "47.9%"
    assert percentage(0.0) == "0.0%"
    assert percentage(1.0) == "100.0%"
    assert percentage(1.5) == "100.0%"


def test_card_render_minimal():
    card = Card(title="Hello", body=["world"])
    text, keyboard = card.render()
    # Title lands inside an HTML <b> tag and the body line follows below.
    # blockquote wrapping only fires when ``quote`` is set; see test below.
    assert "<b>Hello</b>" in text
    assert "world" in text
    assert keyboard is None


def test_card_render_quote_uses_blockquote():
    card = Card(title="Hello", body=["world"], quote="a user message")
    text, _ = card.render()
    assert "<blockquote>a user message</blockquote>" in text


def test_card_steps_and_status():
    card = Card(
        title="Converting",
        steps=(3, 4),
        status_line="Converting Format",
        body=["doing stuff"],
    )
    text, _ = card.render()
    assert "Step 3/4" in text
    assert "Converting Format" in text


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
