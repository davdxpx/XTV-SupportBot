"""Entry point for the XTVfeedback-bot.

Run with ``python main.py``. Requires a populated ``.env`` file.
"""
from __future__ import annotations

import asyncio

from pyrogram import idle

from app.bootstrap import build_client, build_context, shutdown
from app.core.logger import configure_logging, get_logger
from app.core.router import register_all
from app.tasks import autoclose_task, sla_task
from app.tasks.sla_task import SLA_LOOP_SECONDS


async def _amain() -> None:
    configure_logging()
    log = get_logger("main")
    client = build_client()
    await client.start()
    log.info("bot.started")
    try:
        ctx = await build_context(client)
        register_all(client, ctx)
        await ctx.tasks.start()
        await ctx.broadcasts.resume_pending()
        ctx.tasks.run_loop(
            lambda: sla_task.run_once(ctx.sla), name="sla_loop", interval=SLA_LOOP_SECONDS
        )
        ctx.tasks.run_loop(
            lambda: autoclose_task.run_once(client, ctx.db),
            name="autoclose_loop",
            interval=max(60, ctx.settings.AUTO_CLOSE_SWEEP_MINUTES * 60),
        )
        log.info("bot.ready")
        await idle()
        await ctx.tasks.stop()
    finally:
        try:
            await client.stop()
        except Exception:  # noqa: BLE001
            pass
        await shutdown()
        log.info("bot.stopped")


def entrypoint() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    entrypoint()

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
