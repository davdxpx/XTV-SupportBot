from __future__ import annotations

from xtv_support.core.context import HandlerContext
from xtv_support.services.external_directory.model import DirectoryProviderLike, ResolvedUserSignal


async def get_user_signal_for(ctx: HandlerContext, user_id: int) -> ResolvedUserSignal:
    """Convenience accessor to fetch the resolved user signal for a given user.

    This resolves the DirectoryProviderLike from the container and delegates to it.
    """
    provider = ctx.container.resolve(DirectoryProviderLike)
    return await provider.get_signal(user_id)
