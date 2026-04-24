"""Pluggable action registry.

An :class:`Action` is a thin callable: given an :class:`ActionContext`
and a parameter dict, it does one thing and returns an
:class:`ActionResult`. The registry owns the name → Action mapping so
plugins can add their own (``registry.register(MyAction())``) without
touching the executor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # pragma: no cover
    from xtv_support.services.actions.executor import ActionContext, ActionResult


class Action(Protocol):
    """Anything the executor can run."""

    name: str

    async def execute(
        self,
        ctx: ActionContext,
        *,
        ticket: dict | None,
        params: dict,
    ) -> ActionResult: ...


class ActionRegistry:
    """Name → :class:`Action` mapping."""

    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def register(self, action: Action) -> None:
        if not action.name:
            raise ValueError("Action.name must be non-empty")
        self._actions[action.name] = action

    def get(self, name: str) -> Action | None:
        return self._actions.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._actions))


default_registry = ActionRegistry()
