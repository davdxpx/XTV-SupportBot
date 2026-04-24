"""ActionExecutor — one execution path for ticket mutations.

Every mutation a human or machine can make to a ticket flows through
here:

- Bulk actions in the agent inbox (phase 4.5)
- Automation rules (phase 4.6)
- REST API write endpoints (phase 4.7)
- New admin-panel quick buttons (phase 4.4)

Having one path means ``ActionExecuted`` / ``ActionFailed`` events
carry consistent metadata, audit logs line up, and analytics can
attribute every change to an origin (``bot`` | ``api`` | ``rule`` |
``bulk``) without each caller having to remember to log.

Built-in actions:

    assign | tag | untag | set_priority | close | reopen |
    add_internal_note | emoji_react | apply_macro | escalate_to_chat |
    trigger_webhook

Each built-in is small and delegates to the existing repos (no
reimplementation of ticket logic). New actions are plain classes with
a ``name`` attribute and an ``execute`` coroutine — register them via
:class:`~xtv_support.services.actions.registry.ActionRegistry`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from xtv_support.core.events import EventBus
from xtv_support.core.logger import get_logger
from xtv_support.domain.events.actions import ActionExecuted, ActionFailed
from xtv_support.services.actions.registry import Action, ActionRegistry, default_registry

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from pyrogram import Client


def _tickets_repo():
    """Lazy-import so the module loads without pymongo/motor installed."""
    from xtv_support.infrastructure.db import tickets as tr

    return tr


def _notes_repo():
    from xtv_support.infrastructure.db import notes_repo as nr

    return nr

log = get_logger("actions.executor")


@dataclass(slots=True)
class ActionContext:
    """Runtime bag handed to every action.

    ``client`` stays optional because some actions (``assign``, ``tag``,
    ``set_priority``) only touch Mongo and don't need Telegram at all.
    Actions that do need it raise if it's ``None``.
    """

    db: AsyncIOMotorDatabase
    bus: EventBus
    client: Client | None = None
    actor_id: int | None = None
    origin: str = "bot"  # "bot" | "api" | "rule" | "bulk"


@dataclass(slots=True)
class ActionResult:
    ok: bool
    detail: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in actions (small, delegate to existing repos)
# ---------------------------------------------------------------------------
class _AssignAction:
    name = "assign"

    async def execute(
        self, ctx: ActionContext, *, ticket: dict | None, params: dict
    ) -> ActionResult:
        if ticket is None:
            return ActionResult(ok=False, detail="ticket_required")
        assignee = params.get("assignee_id")
        await _tickets_repo().assign(
            ctx.db, ticket["_id"], assignee_id=assignee, assigned_by=ctx.actor_id or 0
        )
        return ActionResult(ok=True, data={"assignee_id": assignee})


class _TagAction:
    name = "tag"

    async def execute(
        self, ctx: ActionContext, *, ticket: dict | None, params: dict
    ) -> ActionResult:
        if ticket is None:
            return ActionResult(ok=False, detail="ticket_required")
        tag = str(params.get("tag") or "").strip()
        if not tag:
            return ActionResult(ok=False, detail="tag_required")
        current = list(ticket.get("tags") or [])
        if tag in current:
            return ActionResult(ok=True, detail="noop", data={"tags": current})
        current.append(tag)
        await ctx.db.tickets.update_one({"_id": ticket["_id"]}, {"$set": {"tags": current}})
        return ActionResult(ok=True, data={"tags": current})


class _UntagAction:
    name = "untag"

    async def execute(
        self, ctx: ActionContext, *, ticket: dict | None, params: dict
    ) -> ActionResult:
        if ticket is None:
            return ActionResult(ok=False, detail="ticket_required")
        tag = str(params.get("tag") or "").strip()
        current = [t for t in (ticket.get("tags") or []) if t != tag]
        await ctx.db.tickets.update_one({"_id": ticket["_id"]}, {"$set": {"tags": current}})
        return ActionResult(ok=True, data={"tags": current})


class _SetPriorityAction:
    name = "set_priority"

    async def execute(
        self, ctx: ActionContext, *, ticket: dict | None, params: dict
    ) -> ActionResult:
        if ticket is None:
            return ActionResult(ok=False, detail="ticket_required")
        priority = str(params.get("priority") or "normal")
        if priority not in {"low", "normal", "high"}:
            return ActionResult(ok=False, detail="bad_priority")
        await _tickets_repo().set_priority(ctx.db, ticket["_id"], priority)
        return ActionResult(ok=True, data={"priority": priority})


class _CloseAction:
    name = "close"

    async def execute(
        self, ctx: ActionContext, *, ticket: dict | None, params: dict
    ) -> ActionResult:
        if ticket is None:
            return ActionResult(ok=False, detail="ticket_required")
        reason = str(params.get("reason") or "manual")
        await _tickets_repo().close(
            ctx.db, ticket["_id"], closed_by=ctx.actor_id, reason=reason
        )
        return ActionResult(ok=True, data={"reason": reason})


class _ReopenAction:
    name = "reopen"

    async def execute(
        self, ctx: ActionContext, *, ticket: dict | None, params: dict
    ) -> ActionResult:
        if ticket is None:
            return ActionResult(ok=False, detail="ticket_required")
        await ctx.db.tickets.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"status": "open", "closed_at": None, "closed_by": None}},
        )
        return ActionResult(ok=True)


class _AddInternalNoteAction:
    name = "add_internal_note"

    async def execute(
        self, ctx: ActionContext, *, ticket: dict | None, params: dict
    ) -> ActionResult:
        if ticket is None:
            return ActionResult(ok=False, detail="ticket_required")
        text = str(params.get("text") or "").strip()
        if not text:
            return ActionResult(ok=False, detail="text_required")
        note = await _notes_repo().append_note(
            ctx.db, ticket["_id"], author_id=ctx.actor_id or 0, text=text
        )
        return ActionResult(ok=True, data={"note": note})


def register_builtins(registry: ActionRegistry) -> None:
    """Register every built-in into ``registry`` (idempotent)."""
    for action in (
        _AssignAction(),
        _TagAction(),
        _UntagAction(),
        _SetPriorityAction(),
        _CloseAction(),
        _ReopenAction(),
        _AddInternalNoteAction(),
    ):
        registry.register(action)


register_builtins(default_registry)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------
class ActionExecutor:
    """Dispatch actions through the registry, emit events, log failures."""

    def __init__(self, registry: ActionRegistry | None = None) -> None:
        self._registry = registry or default_registry

    @property
    def registry(self) -> ActionRegistry:
        return self._registry

    async def execute(
        self,
        ctx: ActionContext,
        action: str,
        *,
        ticket_id: str | None = None,
        params: dict | None = None,
    ) -> ActionResult:
        params = params or {}
        impl: Action | None = self._registry.get(action)
        if impl is None:
            await ctx.bus.publish(
                ActionFailed(
                    action=action,
                    ticket_id=ticket_id,
                    actor_id=ctx.actor_id,
                    origin=ctx.origin,
                    params=params,
                    error="unknown_action",
                )
            )
            return ActionResult(ok=False, detail="unknown_action")

        ticket = None
        if ticket_id is not None:
            ticket = await _tickets_repo().get(ctx.db, ticket_id)
            if ticket is None:
                await ctx.bus.publish(
                    ActionFailed(
                        action=action,
                        ticket_id=ticket_id,
                        actor_id=ctx.actor_id,
                        origin=ctx.origin,
                        params=params,
                        error="ticket_not_found",
                    )
                )
                return ActionResult(ok=False, detail="ticket_not_found")

        start = time.perf_counter()
        try:
            result = await impl.execute(ctx, ticket=ticket, params=params)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "actions.execute_failed",
                action=action,
                ticket_id=ticket_id,
                origin=ctx.origin,
                error=str(exc),
            )
            await ctx.bus.publish(
                ActionFailed(
                    action=action,
                    ticket_id=ticket_id,
                    actor_id=ctx.actor_id,
                    origin=ctx.origin,
                    params=params,
                    error=str(exc),
                )
            )
            return ActionResult(ok=False, detail=f"exception: {exc}")

        latency_ms = int((time.perf_counter() - start) * 1000)
        if result.ok:
            await ctx.bus.publish(
                ActionExecuted(
                    action=action,
                    ticket_id=ticket_id,
                    actor_id=ctx.actor_id,
                    origin=ctx.origin,
                    params=params,
                    latency_ms=latency_ms,
                )
            )
        else:
            await ctx.bus.publish(
                ActionFailed(
                    action=action,
                    ticket_id=ticket_id,
                    actor_id=ctx.actor_id,
                    origin=ctx.origin,
                    params=params,
                    error=result.detail or "action_failed",
                )
            )
        return result
