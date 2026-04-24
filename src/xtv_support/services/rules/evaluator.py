"""RuleEvaluator — subscribes to the EventBus and runs matching rules.

Supported triggers (event class names):

    TicketCreated | TicketAssigned | TicketTagged |
    TicketPriorityChanged | TicketClosed | TicketReopened |
    SlaWarned | SlaBreached

Each trigger carries a ``ticket_id`` attribute, which the evaluator uses
to hydrate the ticket document before checking conditions. Actions run
sequentially through the ActionExecutor with ``origin="rule"``.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from xtv_support.core.events import EventBus
from xtv_support.core.logger import get_logger
from xtv_support.domain.events.rules import RuleExecuted, RuleSkipped
from xtv_support.domain.events.sla import SlaBreached, SlaWarned
from xtv_support.domain.events.tickets import (
    TicketAssigned,
    TicketClosed,
    TicketCreated,
    TicketPriorityChanged,
    TicketReopened,
    TicketTagged,
)
from xtv_support.services.actions.executor import ActionContext, ActionExecutor
from xtv_support.services.rules.cooldown import can_fire, mark_fired
from xtv_support.services.rules.model import Rule, all_conditions_match
from xtv_support.services.rules.repository import list_rules

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from pyrogram import Client

log = get_logger("rules.evaluator")

_TRIGGER_CLASSES: tuple[type, ...] = (
    TicketCreated,
    TicketAssigned,
    TicketTagged,
    TicketPriorityChanged,
    TicketClosed,
    TicketReopened,
    SlaWarned,
    SlaBreached,
)


class RuleEvaluator:
    """Glue between EventBus, rules repository, and ActionExecutor."""

    def __init__(
        self,
        *,
        db: AsyncIOMotorDatabase,
        bus: EventBus,
        actions: ActionExecutor,
        client: Client | None = None,
    ) -> None:
        self._db = db
        self._bus = bus
        self._actions = actions
        self._client = client

    def attach(self) -> None:
        """Subscribe to every supported trigger. Idempotent-enough for boot."""
        for cls in _TRIGGER_CLASSES:
            self._bus.subscribe(cls, self._on_event)
        log.info("rules.evaluator.attached", triggers=len(_TRIGGER_CLASSES))

    async def _on_event(self, event: Any) -> None:
        trigger = event.__class__.__name__
        ticket_id = getattr(event, "ticket_id", None)
        ticket = await self._hydrate_ticket(ticket_id)

        rules = await list_rules(self._db, enabled_only=True, trigger=trigger)
        for rule in rules:
            await self._try_fire(rule, trigger=trigger, ticket_id=ticket_id, ticket=ticket)

    async def _hydrate_ticket(self, ticket_id: str | None) -> dict | None:
        if ticket_id is None:
            return None
        try:
            from xtv_support.infrastructure.db import tickets as tickets_repo

            return await tickets_repo.get(self._db, ticket_id)
        except Exception:  # noqa: BLE001
            return None

    async def _try_fire(
        self,
        rule: Rule,
        *,
        trigger: str,
        ticket_id: str | None,
        ticket: dict | None,
    ) -> None:
        if ticket is not None and not all_conditions_match(rule.conditions, ticket):
            await self._bus.publish(
                RuleSkipped(
                    rule_id=rule.id,
                    ticket_id=ticket_id,
                    trigger=trigger,
                    reason="conditions_unmet",
                )
            )
            return

        if not await can_fire(
            self._db, rule_id=rule.id, ticket_id=ticket_id, cooldown_s=rule.cooldown_s
        ):
            await self._bus.publish(
                RuleSkipped(
                    rule_id=rule.id,
                    ticket_id=ticket_id,
                    trigger=trigger,
                    reason="cooldown",
                )
            )
            return

        start = time.perf_counter()
        exec_ctx = ActionContext(
            db=self._db, bus=self._bus, client=self._client, actor_id=None, origin="rule"
        )
        succeeded = 0
        failed = 0
        for action in rule.actions:
            result = await self._actions.execute(
                exec_ctx,
                action.name,
                ticket_id=ticket_id,
                params=dict(action.params or {}),
            )
            if result.ok:
                succeeded += 1
            else:
                failed += 1
        latency = int((time.perf_counter() - start) * 1000)

        await mark_fired(self._db, rule_id=rule.id, ticket_id=ticket_id)
        await self._bus.publish(
            RuleExecuted(
                rule_id=rule.id,
                ticket_id=ticket_id,
                trigger=trigger,
                actions_succeeded=succeeded,
                actions_failed=failed,
                latency_ms=latency,
            )
        )
