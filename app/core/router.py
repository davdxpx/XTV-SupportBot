from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logger import get_logger

if TYPE_CHECKING:
    from pyrogram import Client

    from app.core.context import HandlerContext

log = get_logger("router")


def register_all(client: "Client", ctx: "HandlerContext") -> None:
    """Register every handler module. Import order controls group dispatch
    implicitly through each handler's ``group=`` argument (see constants.HandlerGroup)."""
    from app.core.context import bind_context

    bind_context(client, ctx)

    # Middleware (negative groups) runs first.
    from app.middlewares import logging_mw  # noqa: F401
    from app.middlewares import blocked_mw  # noqa: F401
    from app.middlewares import cooldown_mw  # noqa: F401

    # Commands (group 0).
    from app.handlers import start  # noqa: F401
    from app.handlers.admin import dashboard  # noqa: F401
    from app.handlers.admin import projects  # noqa: F401
    from app.handlers.admin import contact_links  # noqa: F401
    from app.handlers.admin import block  # noqa: F401
    from app.handlers.admin import broadcast  # noqa: F401
    from app.handlers.admin import assign  # noqa: F401
    from app.handlers.admin import tags  # noqa: F401

    # Admin state machine (group 1).
    from app.handlers.admin import input_router  # noqa: F401

    # User flows (group 2).
    from app.handlers.user import feedback  # noqa: F401
    from app.handlers.user import close as user_close  # noqa: F401
    from app.handlers.user import history  # noqa: F401

    # Topic (group 3).
    from app.handlers.topic import reply  # noqa: F401
    from app.handlers.topic import commands as topic_commands  # noqa: F401

    # Error handler (catch-all).
    from app.handlers import errors as error_handler  # noqa: F401

    modules: list[str] = []
    for module_name in (
        "app.middlewares.logging_mw",
        "app.middlewares.blocked_mw",
        "app.middlewares.cooldown_mw",
        "app.handlers.start",
        "app.handlers.admin.dashboard",
        "app.handlers.admin.projects",
        "app.handlers.admin.contact_links",
        "app.handlers.admin.block",
        "app.handlers.admin.broadcast",
        "app.handlers.admin.assign",
        "app.handlers.admin.tags",
        "app.handlers.admin.input_router",
        "app.handlers.user.feedback",
        "app.handlers.user.close",
        "app.handlers.user.history",
        "app.handlers.topic.reply",
        "app.handlers.topic.commands",
        "app.handlers.errors",
    ):
        modules.append(module_name)

    log.info("handlers.registered", count=len(modules), modules=modules)

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
