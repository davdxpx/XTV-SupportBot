from __future__ import annotations


class BotError(Exception):
    """Base class for all bot-level errors."""


class ConfigError(BotError):
    """Invalid or missing configuration."""


class TopicCreationError(BotError):
    """Raised when a forum topic could not be created."""


class TopicsNotSupported(TopicCreationError):
    """Target chat has forum topics disabled or bot lacks the required permission."""


class TicketNotFound(BotError):
    """Ticket lookup failed."""


class RateLimited(BotError):
    """Raised by the cooldown middleware when a user exceeds the allowed rate."""

    def __init__(self, retry_after: int):
        super().__init__(f"Rate limited, retry after {retry_after}s")
        self.retry_after = retry_after


class AdminOnly(BotError):
    """Raised when a non-admin tries to trigger an admin-only action."""

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
