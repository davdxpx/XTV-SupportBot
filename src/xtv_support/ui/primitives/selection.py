"""Selection list — checkbox UI for bulk actions and rule conditions.

A selection is a small state bag + renderer:

    state = SelectionState(items=[...])
    state.toggle("abc")
    ui = render_selection(state, ...)

The state is pure, so an outer handler can stash it in the user FSM
between callbacks.  ``render_selection`` returns ``(text, keyboard)``
ready for :func:`~xtv_support.ui.primitives.card.send_card` /
``edit_card``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from pyrogram.types import InlineKeyboardMarkup

CHECK = "☑"  # ☑
UNCHECK = "☐"  # ☐


@dataclass(frozen=True, slots=True)
class SelectionItem:
    key: str
    label: str
    hint: str | None = None


@dataclass
class SelectionState:
    items: tuple[SelectionItem, ...] = ()
    selected: set[str] = field(default_factory=set)

    # ------------------------------------------------------------------
    def toggle(self, key: str) -> None:
        if key in self.selected:
            self.selected.discard(key)
        else:
            self.selected.add(key)

    def select_all(self) -> None:
        self.selected = {it.key for it in self.items}

    def clear(self) -> None:
        self.selected.clear()

    @property
    def count(self) -> int:
        return len(self.selected)


@dataclass(frozen=True, slots=True)
class SelectionAction:
    label: str
    callback: str


def selection_specs(
    state: SelectionState,
    *,
    toggle_cb: str,
    select_all_cb: str,
    clear_cb: str,
    apply_actions: Iterable[SelectionAction] = (),
    back_cb: str | None = None,
) -> list[list[dict[str, str]]]:
    """Pyrogram-free keyboard description. Tests call this directly."""
    rows: list[list[dict[str, str]]] = []
    for it in state.items:
        box = CHECK if it.key in state.selected else UNCHECK
        hint = f" — {it.hint}" if it.hint else ""
        rows.append(
            [
                {
                    "label": f"{box} {it.label}{hint}",
                    "callback": f"{toggle_cb}:{it.key}",
                }
            ]
        )
    rows.append(
        [
            {"label": "Select all", "callback": select_all_cb},
            {"label": "Clear", "callback": clear_cb},
        ]
    )
    for action in apply_actions:
        rows.append([{"label": action.label, "callback": action.callback}])
    if back_cb is not None:
        rows.append([{"label": "◀ Back", "callback": back_cb}])
    return rows


def render_selection(
    state: SelectionState,
    *,
    title: str,
    toggle_cb: str,
    select_all_cb: str,
    clear_cb: str,
    apply_actions: Iterable[SelectionAction] = (),
    back_cb: str | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """Render a selection list with per-row toggles + control row."""
    lines: list[str] = [f"<b>{title}</b>", ""]
    if not state.items:
        lines.append("<i>Nothing to show.</i>")
    else:
        lines.append(f"Selected: <b>{state.count}</b> / {len(state.items)}")

    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    specs = selection_specs(
        state,
        toggle_cb=toggle_cb,
        select_all_cb=select_all_cb,
        clear_cb=clear_cb,
        apply_actions=apply_actions,
        back_cb=back_cb,
    )
    pyrogram_rows: list[list[Any]] = []
    for row in specs:
        built: list[Any] = []
        for cell in row:
            if "url" in cell:
                built.append(InlineKeyboardButton(cell["label"], url=cell["url"]))
            else:
                built.append(InlineKeyboardButton(cell["label"], callback_data=cell["callback"]))
        pyrogram_rows.append(built)
    return "\n".join(lines), InlineKeyboardMarkup(pyrogram_rows)
