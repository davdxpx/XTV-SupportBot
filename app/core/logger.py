# --- Imports ---
from __future__ import annotations

import logging
import sys
from typing import Any

from app.config import settings


# === Classes ===
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"


class ConsoleFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "\U0001F41E",  # 🐞
        logging.INFO: "\u2139\ufe0f ",  # ℹ️
        logging.WARNING: "\u26a0\ufe0f ",  # ⚠️
        logging.ERROR: "\u274c ",  # ❌
        logging.CRITICAL: "\U0001F525 ",  # 🔥
    }

    COLOR_MAP = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED + Colors.BOLD,
        logging.CRITICAL: Colors.RED + Colors.BOLD,
    }

    # Cache formatters per level to avoid re-creating on every .format() call
    _cached_formatters: dict[int, logging.Formatter] = {}

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno not in self._cached_formatters:
            emoji = self.FORMATS.get(record.levelno, "")
            color = self.COLOR_MAP.get(record.levelno, Colors.RESET)
            log_fmt = (
                f"{Colors.BLUE}[%(asctime)s]{Colors.RESET} "
                f"{color}{emoji}%(levelname)-8s{Colors.RESET} :: "
                f"{color}%(name)s{Colors.RESET} :: "
                f"{color}%(message)s{Colors.RESET}"
            )
            self._cached_formatters[record.levelno] = logging.Formatter(
                log_fmt, datefmt="%H:%M:%S"
            )
        return self._cached_formatters[record.levelno].format(record)


# Reserved keyword args that stdlib logging accepts; anything else is treated
# as structured context and appended to the message as ``key=value`` pairs.
_RESERVED_KWARGS = {"exc_info", "extra", "stack_info", "stacklevel"}


def _merge_kwargs(msg: Any, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    reserved: dict[str, Any] = {}
    extras: dict[str, Any] = {}
    for k, v in kwargs.items():
        (reserved if k in _RESERVED_KWARGS else extras)[k] = v

    msg_str = str(msg)
    if extras:
        parts = " ".join(f"{k}={v!r}" if isinstance(v, str) and (" " in v or not v) else f"{k}={v}" for k, v in extras.items())
        msg_str = f"{msg_str} {parts}" if msg_str else parts
    return msg_str, reserved


class BotLogger(logging.Logger):
    """Accepts ``log.info('event', key=value, ...)`` style calls in addition
    to the regular stdlib interface. Extra kwargs are rendered as
    ``key=value`` pairs and appended to the message so the pretty console
    formatter in :class:`ConsoleFormatter` stays in charge of styling."""

    def _log_with_kwargs(
        self, level: int, msg: Any, args: tuple, **kwargs: Any
    ) -> None:
        msg_str, reserved = _merge_kwargs(msg, kwargs)
        if self.isEnabledFor(level):
            # Delegate to stdlib with reserved kwargs preserved.
            self._log(level, msg_str, args, **reserved)

    def debug(self, msg: Any = "", *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._log_with_kwargs(logging.DEBUG, msg, args, **kwargs)

    def info(self, msg: Any = "", *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._log_with_kwargs(logging.INFO, msg, args, **kwargs)

    def warning(self, msg: Any = "", *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._log_with_kwargs(logging.WARNING, msg, args, **kwargs)

    def error(self, msg: Any = "", *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._log_with_kwargs(logging.ERROR, msg, args, **kwargs)

    def critical(self, msg: Any = "", *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._log_with_kwargs(logging.CRITICAL, msg, args, **kwargs)

    def exception(self, msg: Any = "", *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        kwargs.setdefault("exc_info", True)
        self._log_with_kwargs(logging.ERROR, msg, args, **kwargs)


# Install our logger class for every logger created from now on.
logging.setLoggerClass(BotLogger)


# Set third-party log levels once at module load
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("motor").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


# Shared handler instance
_console_handler: logging.Handler | None = None
_configured = False


# === Helper Functions ===
def _level_for_settings() -> int:
    level_name = (settings.LOG_LEVEL or "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging() -> None:
    """Idempotent. Attach the shared console handler to the root logger."""
    global _console_handler, _configured
    if _configured:
        return
    root = logging.getLogger()
    root.setLevel(_level_for_settings())
    if _console_handler is None:
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setFormatter(ConsoleFormatter())
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(_console_handler)
    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    global _console_handler
    configure_logging()
    logger = logging.getLogger(name or "xtv")
    logger.setLevel(_level_for_settings())
    if not logger.handlers:
        if _console_handler is None:
            _console_handler = logging.StreamHandler(sys.stdout)
            _console_handler.setFormatter(ConsoleFormatter())
        logger.addHandler(_console_handler)
        logger.propagate = False
    return logger


# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
