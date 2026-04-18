from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from pyrogram import Client

    from app.config import Settings
    from app.services.broadcast_service import BroadcastManager
    from app.services.cooldown_service import CooldownService
    from app.services.sla_service import SlaService
    from app.tasks.scheduler import TaskManager


@dataclass
class HandlerContext:
    """Shared dependencies passed to handlers.

    Pyrofork handlers receive only (client, update). We stash this on the
    Client instance as ``client._ctx`` in ``register_all`` so handlers can
    access it via ``ctx = client._ctx``.
    """

    client: "Client"
    settings: "Settings"
    db: "AsyncIOMotorDatabase"
    tasks: "TaskManager"
    cooldown: "CooldownService"
    sla: "SlaService"
    broadcasts: "BroadcastManager"


def bind_context(client: "Client", ctx: HandlerContext) -> None:
    client._ctx = ctx  # type: ignore[attr-defined]


def get_context(client: "Client") -> HandlerContext:
    ctx: HandlerContext | None = getattr(client, "_ctx", None)
    if ctx is None:
        raise RuntimeError("HandlerContext not bound to client; call bind_context first.")
    return ctx
