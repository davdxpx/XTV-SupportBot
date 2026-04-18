from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from app.core.logger import get_logger

if TYPE_CHECKING:
    from pyrogram import Client

    from app.core.context import HandlerContext

log = get_logger("router")

# Every module that defines @Client.on_message / @Client.on_callback_query
# handlers. Order is irrelevant for correctness because the explicit
# ``group=`` argument on each decorator controls dispatch order, but the
# import order does pin the per-group registration order if multiple
# handlers share the same group.
_HANDLER_MODULES: tuple[str, ...] = (
    # Middleware (negative groups)
    "app.middlewares.logging_mw",
    "app.middlewares.blocked_mw",
    "app.middlewares.cooldown_mw",
    # Commands (group 0)
    "app.handlers.start",
    "app.handlers.admin.dashboard",
    "app.handlers.admin.projects",
    "app.handlers.admin.contact_links",
    "app.handlers.admin.block",
    "app.handlers.admin.broadcast",
    "app.handlers.admin.assign",
    "app.handlers.admin.tags",
    "app.handlers.user.feedback",
    "app.handlers.user.close",
    "app.handlers.user.history",
    "app.handlers.user.tickets",
    "app.handlers.topic.reply",
    "app.handlers.topic.commands",
    # State machine (group 1)
    "app.handlers.admin.input_router",
    # Catch-all
    "app.handlers.errors",
)


def register_all(client: "Client", ctx: "HandlerContext") -> None:
    """Bind context, import every handler module, then attach every collected
    handler to the live :class:`pyrogram.Client` instance.

    Pyrogram's ``@Client.on_message`` decorator is a *classmethod* that just
    stashes ``handlers`` on the wrapped function. Without
    ``plugins=dict(root=...)`` the dispatcher never sees them. We do the
    plugin-loader's job here explicitly so the registration is independent
    of import-time magic and visible in the logs.
    """
    from app.core.context import bind_context

    bind_context(client, ctx)

    total_handlers = 0
    per_module: list[tuple[str, int]] = []

    for module_name in _HANDLER_MODULES:
        module = importlib.import_module(module_name)
        count = 0
        for attr in dir(module):
            obj = getattr(module, attr)
            handlers = getattr(obj, "handlers", None)
            if not handlers:
                continue
            for entry in handlers:
                # Pyrogram stores either (handler, group) tuples or bare handlers.
                if isinstance(entry, tuple) and len(entry) == 2:
                    handler, group = entry
                else:
                    handler, group = entry, 0
                client.add_handler(handler, group)
                count += 1
        per_module.append((module_name, count))
        total_handlers += count
        log.debug("router.module_loaded", module=module_name, handlers=count)

    log.info("router.registered", modules=len(_HANDLER_MODULES), handlers=total_handlers)
    for name, count in per_module:
        log.info("router.module", module=name, handlers=count)


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
