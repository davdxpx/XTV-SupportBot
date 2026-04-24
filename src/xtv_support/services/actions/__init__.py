"""Action layer — one execution path shared by bot UI, rules engine and API.

Exposes the :class:`ActionExecutor` and the built-in action implementations.
Later phases (4.5 agent cockpit, 4.6 rules engine, 4.7 API write) all go
through the executor, so every mutation to a ticket emits the same
``ActionExecuted`` / ``ActionFailed`` events and the same audit-log entries.
"""

from xtv_support.services.actions.executor import ActionContext, ActionExecutor, ActionResult
from xtv_support.services.actions.registry import Action, ActionRegistry, default_registry

__all__ = [
    "Action",
    "ActionContext",
    "ActionExecutor",
    "ActionRegistry",
    "ActionResult",
    "default_registry",
]
