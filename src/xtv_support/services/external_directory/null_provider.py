"""External User Directory Null Provider.

The fallback provider that acts as the default system state when external directories are not configured.
"""

from __future__ import annotations

from xtv_support.services.external_directory.model import ResolvedUserSignal


class NullDirectoryProvider:
    """A directory provider that does zero I/O and always returns a safe default.

    This is the default bound in the container when no operator has
    configured the External Directory feature, ensuring zero startup cost
    and zero behavior change for existing deployments.
    """

    async def get_signal(self, telegram_user_id: int) -> ResolvedUserSignal:
        """Returns a default, non-VIP signal instantly."""
        return ResolvedUserSignal()
