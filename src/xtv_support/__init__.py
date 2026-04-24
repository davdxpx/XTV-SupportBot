"""XTV-SupportBot — enterprise Telegram support / feedback bot.

Public API is intentionally minimal. Consumers import submodules directly
(``from xtv_support.services.tickets import service``). Only the version
and the CLI ``entrypoint`` are exposed at top level.
"""

from __future__ import annotations

from xtv_support.version import VERSION, __version__

__all__ = ["VERSION", "__version__", "entrypoint"]


def entrypoint() -> None:
    """Console-script entry point. Re-exports ``__main__.entrypoint`` lazily."""
    from xtv_support.__main__ import entrypoint as _main

    _main()
