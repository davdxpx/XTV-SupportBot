"""Entry point for the XTVfeedback-bot.

Run with ``python main.py``. Requires a populated ``.env`` file.
"""
from __future__ import annotations

import asyncio
import platform
import sys

from pyrogram import idle
from pyrogram.errors import RPCError

from app.bootstrap import build_client, build_context, shutdown
from app.config import settings
from app.core.logger import configure_logging, get_logger
from app.core.router import register_all
from app.tasks import autoclose_task, sla_task
from app.tasks.sla_task import SLA_LOOP_SECONDS


async def _amain() -> None:
    configure_logging()
    log = get_logger("main")

    log.info(
        "boot.environment",
        python=platform.python_version(),
        impl=platform.python_implementation(),
        platform=platform.platform(),
        executable=sys.executable,
    )
    log.info(
        "boot.settings",
        log_level=settings.LOG_LEVEL,
        admin_ids=settings.ADMIN_IDS,
        admin_channel_id=settings.ADMIN_CHANNEL_ID,
        mongo_db=settings.MONGO_DB_NAME,
        sla_warn_minutes=settings.SLA_WARN_MINUTES,
        auto_close_days=settings.AUTO_CLOSE_DAYS,
        cooldown=f"{settings.COOLDOWN_RATE}/{settings.COOLDOWN_WINDOW}s",
        broadcast_concurrency=settings.BROADCAST_CONCURRENCY,
    )

    client = build_client()
    log.info("boot.client_starting")
    await client.start()

    try:
        me = await client.get_me()
        log.info(
            "boot.bot_identity",
            id=me.id,
            username=f"@{me.username}" if me.username else "?",
            name=me.first_name,
            is_bot=me.is_bot,
            can_join_groups=getattr(me, "can_join_groups", None),
            can_read_messages=getattr(me, "can_read_all_group_messages", None),
        )
    except RPCError as exc:
        log.error("boot.get_me_failed", error=str(exc))

    try:
        chat = await client.get_chat(settings.ADMIN_CHANNEL_ID)
        chat_type_str = str(getattr(chat, "type", "?"))
        is_forum = bool(getattr(chat, "is_forum", False)) or chat_type_str.endswith("FORUM")
        log.info(
            "boot.admin_chat",
            id=chat.id,
            title=getattr(chat, "title", None),
            type=chat_type_str,
            is_forum=is_forum,
            members=getattr(chat, "members_count", None),
        )
        if not is_forum:
            log.warning(
                "boot.admin_chat_not_forum",
                hint="Enable Topics in the supergroup so tickets can become threads.",
            )
    except RPCError as exc:
        log.error(
            "boot.admin_chat_unreachable",
            chat_id=settings.ADMIN_CHANNEL_ID,
            error=str(exc),
            hint="Make sure the bot is a member of the supergroup with Manage Topics.",
        )

    try:
        ctx = await build_context(client)
        register_all(client, ctx)
        await ctx.tasks.start()
        await ctx.broadcasts.resume_pending()
        ctx.tasks.run_loop(
            lambda: sla_task.run_once(ctx.sla),
            name="sla_loop",
            interval=SLA_LOOP_SECONDS,
        )
        ctx.tasks.run_loop(
            lambda: autoclose_task.run_once(client, ctx.db),
            name="autoclose_loop",
            interval=max(60, ctx.settings.AUTO_CLOSE_SWEEP_MINUTES * 60),
        )
        log.info(
            "boot.ready",
            handlers="see router.registered above",
            forum_chat=settings.ADMIN_CHANNEL_ID,
            admins=len(settings.ADMIN_IDS),
        )
        log.info("boot.tip", msg="Send /start in a private chat to test the user flow.")
        await idle()
        log.info("shutdown.starting")
        await ctx.tasks.stop()
    finally:
        try:
            await client.stop()
        except Exception as exc:  # noqa: BLE001
            log.warning("shutdown.client_stop_failed", error=str(exc))
        await shutdown()
        log.info("shutdown.done")


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
