from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, InputUserDeactivated, RPCError, UserIsBlocked

from xtv_support.config.settings import settings
from xtv_support.core.logger import get_logger
from xtv_support.infrastructure.db import broadcasts as broadcasts_repo
from xtv_support.infrastructure.db import users as users_repo
from xtv_support.ui.templates import broadcast as broadcast_tmpl

log = get_logger("broadcast")


@dataclass
class BroadcastState:
    bid: ObjectId
    text: str
    total: int
    sent: int = 0
    failed: int = 0
    blocked: int = 0
    paused: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        # paused is NOT set by default: when set the workers pause.
        pass


class BroadcastManager:
    """Drives a single broadcast at a time (persistent across restarts).

    Admins interact via callbacks (pause/resume/cancel). Progress card edits
    are produced in the same task that drives the workers so we stay within
    FloodWait budgets.
    """

    def __init__(self, client: Client, db: AsyncIOMotorDatabase):
        self._client = client
        self._db = db
        self._state: BroadcastState | None = None
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def active(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(
        self, *, bid: ObjectId, text: str, total: int, progress_chat_id: int, progress_msg_id: int
    ) -> None:
        async with self._lock:
            if self.active:
                return
            self._state = BroadcastState(bid=bid, text=text, total=total)
            await broadcasts_repo.set_progress_msg(
                self._db, bid, chat_id=progress_chat_id, msg_id=progress_msg_id
            )
            await broadcasts_repo.set_state(self._db, bid, "running")
            self._task = asyncio.create_task(self._run(progress_chat_id, progress_msg_id))

    async def pause(self) -> None:
        if self._state:
            self._state.paused.set()
            await broadcasts_repo.set_state(self._db, self._state.bid, "paused")

    async def resume(self) -> None:
        if self._state:
            self._state.paused.clear()
            await broadcasts_repo.set_state(self._db, self._state.bid, "running")

    async def cancel(self) -> None:
        if self._state:
            self._state.cancelled.set()
            self._state.paused.clear()

    async def resume_pending(self) -> None:
        """Resume or mark-done any broadcasts left over from a previous run."""
        pending = await broadcasts_repo.find_resumable(self._db)
        for doc in pending:
            # The old process is dead, so we cannot continue sending reliably.
            # Mark the broadcast cancelled to keep the DB state consistent.
            await broadcasts_repo.set_state(self._db, doc["_id"], "cancelled", finished=True)
        if pending:
            log.info("broadcast.resumed_cancelled", count=len(pending))

    async def _run(self, progress_chat_id: int, progress_msg_id: int) -> None:
        assert self._state is not None
        state = self._state

        recipients = await users_repo.iter_active(self._db)
        total = len(recipients)
        if total != state.total:
            state.total = total
            await self._db.broadcasts.update_one({"_id": state.bid}, {"$set": {"total": total}})

        semaphore = asyncio.Semaphore(settings.BROADCAST_CONCURRENCY)

        async def _send(rcpt: dict[str, Any]) -> None:
            if state.cancelled.is_set():
                return
            if state.paused.is_set():
                await state.paused.wait()
            async with semaphore:
                try:
                    await self._client.send_message(
                        rcpt["user_id"], state.text, parse_mode=ParseMode.HTML
                    )
                    state.sent += 1
                    await broadcasts_repo.increment_counters(self._db, state.bid, sent=1)
                except FloodWait as exc:
                    wait = int(getattr(exc, "value", 1)) or 1
                    await asyncio.sleep(wait)
                    try:
                        await self._client.send_message(
                            rcpt["user_id"], state.text, parse_mode=ParseMode.HTML
                        )
                        state.sent += 1
                        await broadcasts_repo.increment_counters(self._db, state.bid, sent=1)
                    except RPCError:
                        state.failed += 1
                        await broadcasts_repo.increment_counters(self._db, state.bid, failed=1)
                except (UserIsBlocked, InputUserDeactivated):
                    state.blocked += 1
                    await broadcasts_repo.increment_counters(self._db, state.bid, blocked=1)
                except RPCError:
                    state.failed += 1
                    await broadcasts_repo.increment_counters(self._db, state.bid, failed=1)

        progress_task = asyncio.create_task(self._progress_loop(progress_chat_id, progress_msg_id))

        try:
            coros = [_send(r) for r in recipients]
            for chunk_start in range(0, len(coros), 200):
                if state.cancelled.is_set():
                    break
                await asyncio.gather(*coros[chunk_start : chunk_start + 200])
                await asyncio.sleep(settings.BROADCAST_FLOOD_BUFFER_MS / 1000)
        finally:
            state.cancelled.set()
            await progress_task
            final_state = (
                "cancelled"
                if state.cancelled.is_set()
                and (state.sent + state.failed + state.blocked) < state.total
                else "done"
            )
            await broadcasts_repo.set_state(self._db, state.bid, final_state, finished=True)
            await self._render_final(
                progress_chat_id, progress_msg_id, cancelled=(final_state == "cancelled")
            )
            self._state = None

    async def _progress_loop(self, chat_id: int, msg_id: int) -> None:
        assert self._state is not None
        state = self._state
        card = broadcast_tmpl.running(
            state.text,
            sent=state.sent,
            failed=state.failed,
            blocked=state.blocked,
            total=state.total,
        )
        card._message_id = msg_id
        card._chat_id = chat_id
        while not state.cancelled.is_set():
            await asyncio.sleep(settings.PROGRESS_EDIT_INTERVAL)
            is_paused = state.paused.is_set()
            card = (broadcast_tmpl.paused if is_paused else broadcast_tmpl.running)(
                state.text,
                sent=state.sent,
                failed=state.failed,
                blocked=state.blocked,
                total=state.total,
            )
            card._message_id = msg_id
            card._chat_id = chat_id
            try:
                await card.update(
                    self._client, progress=state.sent / max(state.total, 1), force=True
                )
            except RPCError:
                pass

    async def _render_final(self, chat_id: int, msg_id: int, *, cancelled: bool) -> None:
        assert self._state is not None
        state = self._state
        card = broadcast_tmpl.finished(
            state.text,
            sent=state.sent,
            failed=state.failed,
            blocked=state.blocked,
            total=state.total,
            cancelled=cancelled,
        )
        card._message_id = msg_id
        card._chat_id = chat_id
        try:
            await card.finalize(self._client)
        except RPCError:
            pass


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
