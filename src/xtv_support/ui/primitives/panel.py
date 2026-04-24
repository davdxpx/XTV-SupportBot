"""Panel — multi-section dashboard layout built on top of :class:`Card`.

Where a :class:`~xtv_support.ui.primitives.card.Card` is one focused
message (one title, optional body, optional quote), a **Panel** is a
dashboard: a tab strip at the top, stat rows in the middle, optional
drill-down buttons, and a pagination footer. The same primitive backs
the new ``/admin`` control panel and the agent inbox, so the look &
feel stays consistent.

The class owns only the *rendering* — sending, editing and attaching
a pyrofork message is the caller's job (use
:func:`xtv_support.ui.primitives.card.send_card` /
:func:`~xtv_support.ui.primitives.card.edit_card` with the tuple
returned by :meth:`Panel.render`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type-only; runtime import is lazy
    from pyrogram.types import InlineKeyboardMarkup


@dataclass(frozen=True, slots=True)
class Tab:
    key: str
    label: str
    callback: str
    active: bool = False


@dataclass(frozen=True, slots=True)
class StatTile:
    label: str
    value: str
    hint: str | None = None


@dataclass(frozen=True, slots=True)
class PanelButton:
    label: str
    callback: str | None = None
    url: str | None = None
    # When set, the button opens the bundled admin / user Mini-App at
    # ``webapp_url`` inside Telegram. Mutually exclusive with
    # ``callback`` and ``url`` — the first non-empty field wins at
    # render time in this order: webapp_url > url > callback.
    webapp_url: str | None = None


# Horizontal rule drawn between sections. Telegram renders ``━`` as a
# solid, uniform line on every platform, so we use it instead of a
# dashed / Unicode-box alternative that some clients collapse.
HR_RULE = "━" * 20


@dataclass
class Panel:
    """Dashboard-style message.

    Rendering order (all sections optional except ``title``)::

        <b>{title}</b>
        ━━━━━━━━━━━━━━━━━━━━          ← HR (suppressed via ``hr=False``)
        <i>{subtitle}</i>
        {tab strip}                   ← only if tabs were passed
        {stat tiles}
        {body lines}
        <blockquote>{hint[0]}</blockquote>
        <blockquote>{hint[1]}</blockquote>
        ━━━━━━━━━━━━━━━━━━━━          ← HR (omitted if no body/stats/hints)
        {footer}                      ← rendered outside the HR envelope
    """

    title: str
    subtitle: str | None = None
    tabs: Sequence[Tab] = field(default_factory=tuple)
    # Tabs per inline-keyboard row — 4 by default for legacy tab-strip usage.
    # The new drill-down admin UX sets ``tabs=()`` and uses ``action_rows``
    # directly for the 2-column landing grid.
    tabs_per_row: int = 4
    stats: Sequence[StatTile] = field(default_factory=tuple)
    body: Sequence[str] = field(default_factory=tuple)
    # One-liner blockquoted hints rendered between body and closing HR. Use
    # for status messages / tips / footer-style text. Multiple hints stack.
    hints: Sequence[str] = field(default_factory=tuple)
    action_rows: Sequence[Sequence[PanelButton]] = field(default_factory=tuple)
    footer: str | None = None
    page: int | None = None
    total_pages: int | None = None
    page_prev_cb: str | None = None
    page_next_cb: str | None = None
    # Wrap the message in ``━━━…`` horizontal rules so it visually stands out
    # from plain chat messages around it. Default on; turn off for cards that
    # don't need the framing (e.g. short confirmation toasts).
    hr: bool = True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _tab_strip(self) -> str:
        """Render the tab row as text, wrapped to ``tabs_per_row`` per line."""
        if not self.tabs:
            return ""
        per_row = max(1, self.tabs_per_row)
        lines: list[str] = []
        row: list[str] = []
        for tab in self.tabs:
            chip = f"<b>· {tab.label} ·</b>" if tab.active else tab.label
            row.append(chip)
            if len(row) == per_row:
                lines.append("  ".join(row))
                row = []
        if row:
            lines.append("  ".join(row))
        return "\n".join(lines)

    def _stat_block(self) -> str:
        if not self.stats:
            return ""
        lines: list[str] = []
        for tile in self.stats:
            hint = f"  <i>{tile.hint}</i>" if tile.hint else ""
            lines.append(f"<b>{tile.value}</b> — {tile.label}{hint}")
        return "\n".join(lines)

    def _pagination_text(self) -> str:
        if self.page is None or self.total_pages is None:
            return ""
        return f"Page {self.page}/{self.total_pages}"

    def render_text(self) -> str:
        lines: list[str] = [f"<b>{self.title}</b>"]
        if self.hr:
            lines.append(HR_RULE)
        if self.subtitle:
            lines.append(f"<i>{self.subtitle}</i>")
        tabs = self._tab_strip()
        if tabs:
            if lines[-1] != HR_RULE:
                lines.append("")
            lines.append(tabs)
        stats = self._stat_block()
        if stats:
            lines.append("")
            lines.append(stats)
        if self.body:
            lines.append("")
            lines.extend(line.rstrip() for line in self.body)
        for hint in self.hints:
            lines.append("")
            lines.append(f"<blockquote>{hint}</blockquote>")
        pag = self._pagination_text()
        if pag:
            lines.append("")
            lines.append(pag)
        if self.hr:
            lines.append(HR_RULE)
        if self.footer:
            lines.append(self.footer)
        return "\n".join(lines)

    def _row_specs(self) -> list[list[dict[str, str]]]:
        """Pyrogram-free representation of the keyboard (for tests)."""
        rows: list[list[dict[str, str]]] = []

        if self.tabs:
            # Chunk tabs into rows of ``tabs_per_row`` so the keyboard stays
            # readable on mobile instead of a single line of 8 cramped buttons.
            per_row = max(1, self.tabs_per_row)
            chunk: list[dict[str, str]] = []
            for t in self.tabs:
                chunk.append(
                    {
                        "label": (f"· {t.label} ·" if t.active else t.label),
                        "callback": t.callback,
                    }
                )
                if len(chunk) == per_row:
                    rows.append(chunk)
                    chunk = []
            if chunk:
                rows.append(chunk)

        for action_row in self.action_rows:
            if not action_row:
                continue
            row: list[dict[str, str]] = []
            for btn in action_row:
                if btn.webapp_url is not None:
                    row.append({"label": btn.label, "webapp_url": btn.webapp_url})
                elif btn.url is not None:
                    row.append({"label": btn.label, "url": btn.url})
                elif btn.callback is not None:
                    row.append({"label": btn.label, "callback": btn.callback})
            if row:
                rows.append(row)

        if self.page is not None and (self.page_prev_cb or self.page_next_cb):
            nav: list[dict[str, str]] = []
            if self.page_prev_cb:
                nav.append({"label": "◀ Prev", "callback": self.page_prev_cb})
            if self.page_next_cb:
                nav.append({"label": "Next ▶", "callback": self.page_next_cb})
            if nav:
                rows.append(nav)

        return rows

    def render_keyboard(self) -> InlineKeyboardMarkup | None:
        """Build the pyrogram keyboard (lazy-imports so tests don't need pyrogram)."""
        specs = self._row_specs()
        if not specs:
            return None
        from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

        pyrogram_rows: list[list[Any]] = []
        for row in specs:
            built: list[Any] = []
            for cell in row:
                if "webapp_url" in cell:
                    built.append(
                        InlineKeyboardButton(
                            cell["label"], web_app=WebAppInfo(url=cell["webapp_url"])
                        )
                    )
                elif "url" in cell:
                    built.append(InlineKeyboardButton(cell["label"], url=cell["url"]))
                else:
                    built.append(
                        InlineKeyboardButton(cell["label"], callback_data=cell["callback"])
                    )
            pyrogram_rows.append(built)
        return InlineKeyboardMarkup(pyrogram_rows)

    def render(self) -> tuple[str, InlineKeyboardMarkup | None]:
        return self.render_text(), self.render_keyboard()
