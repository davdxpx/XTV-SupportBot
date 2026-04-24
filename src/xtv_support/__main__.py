"""Executable entry — ``python -m xtv_support`` / ``python main.py``.

Orchestrates the boot sequence: configure logging, construct the Telegram
client, build the handler context, register handlers + background loops,
optionally start the REST API, then idle. Business-logic factories live
in :mod:`xtv_support.core.bootstrap`.
"""

from __future__ import annotations

import asyncio
import contextlib
import platform
import sys

from pyrogram import idle
from pyrogram.errors import RPCError

from xtv_support.config.settings import settings
from xtv_support.core.bootstrap import build_client, build_context, shutdown
from xtv_support.core.logger import configure_logging, get_logger
from xtv_support.core.router import register_all
from xtv_support.tasks import autoclose_task, sla_task
from xtv_support.tasks.sla_task import SLA_LOOP_SECONDS


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

    await _maybe_set_menu_button(client, log)

    api_server: _UvicornRunner | None = None
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

        if settings.API_ENABLED:
            api_server = await _start_api(ctx.db)
            log.info(
                "boot.api_started",
                host=settings.API_HOST,
                port=settings.effective_api_port,
                cors_origins=settings.cors_origins or "<none>",
            )
        else:
            log.info(
                "boot.api_disabled",
                hint="Set API_ENABLED=true to expose /health, /ready, /api/v1/*",
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
        if api_server is not None:
            await api_server.stop()
        await ctx.tasks.stop()
    finally:
        try:
            await client.stop()
        except Exception as exc:  # noqa: BLE001
            log.warning("shutdown.client_stop_failed", error=str(exc))
        await shutdown()
        log.info("shutdown.done")


class _UvicornRunner:
    """Lightweight wrapper around ``uvicorn.Server`` that co-exists with pyrofork.

    Uvicorn's ``Server.serve()`` is an async coroutine — we schedule it as
    a background task on the same event loop the Telegram client uses,
    so both share one process, one loop, and one Mongo client.
    """

    def __init__(self, server: uvicorn.Server) -> None:  # type: ignore[name-defined] # noqa: F821
        self._server = server
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._server.serve(), name="uvicorn.serve")
        # Give uvicorn a moment to bind the socket so the ``boot.ready``
        # log line reflects the actual state.
        for _ in range(50):  # ~5s max
            if self._server.started:
                return
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._server.should_exit = True
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await asyncio.wait_for(self._task, timeout=10)
        self._task = None


async def _start_api(db) -> _UvicornRunner:
    """Build the FastAPI app + spawn uvicorn as a background task."""
    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - guarded by requirements.txt
        raise RuntimeError(
            "API_ENABLED=true but uvicorn is not installed. "
            "Install with `pip install 'xtv-support[api]'` or add "
            "fastapi + uvicorn[standard] to requirements.txt."
        ) from exc

    from xtv_support.api.server import create_app

    app = create_app(db=db)

    if settings.cors_origins:
        try:
            from fastapi.middleware.cors import CORSMiddleware

            app.add_middleware(
                CORSMiddleware,
                allow_origins=settings.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        except ModuleNotFoundError:  # pragma: no cover
            pass

    config = uvicorn.Config(
        app,
        host=settings.API_HOST,
        port=settings.effective_api_port,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        # We own the loop (pyrofork runs on it) — let uvicorn reuse it.
        loop="asyncio",
        lifespan="off",
    )
    server = uvicorn.Server(config)
    runner = _UvicornRunner(server)
    await runner.start()
    return runner


async def _maybe_set_menu_button(client, log) -> None:
    """Wire the global Mini-App "Open App" button into every chat.

    No-op unless ``WEBAPP_SET_MENU_BUTTON=true`` and ``WEBAPP_URL`` is
    a non-empty ``https://`` URL. Failure is logged but never fatal —
    the bot still boots in chat-only mode if Telegram rejects the
    call (e.g. because the WebApp domain isn't configured on BotFather).
    """
    if not settings.WEBAPP_SET_MENU_BUTTON:
        return
    url = (settings.WEBAPP_URL or "").strip()
    if not url.startswith("https://"):
        log.warning(
            "boot.webapp_menu_skipped",
            reason="WEBAPP_URL missing or not https",
            url=url or "<empty>",
        )
        return
    try:
        from pyrogram.raw.functions.bots import SetBotMenuButton
        from pyrogram.raw.types import BotMenuButtonWebApp, InputUserEmpty

        button = BotMenuButtonWebApp(
            text=settings.WEBAPP_MENU_BUTTON_TEXT or "Open App",
            url=url,
        )
        # ``InputUserEmpty`` targets every chat the bot is in — per-user
        # overrides would use ``InputUser(user_id=…)``.
        await client.invoke(SetBotMenuButton(user_id=InputUserEmpty(), button=button))
        log.info("boot.webapp_menu_set", url=url, text=button.text)
    except Exception as exc:  # noqa: BLE001 — informational; never fatal
        log.warning("boot.webapp_menu_failed", error=str(exc))


def entrypoint() -> None:
    """Synchronous wrapper — runs :func:`_amain` inside ``asyncio.run``."""
    asyncio.run(_amain())


if __name__ == "__main__":
    entrypoint()
