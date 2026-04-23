from __future__ import annotations

from app.core.logger import get_logger
from app.services.sla_service import SlaService

log = get_logger("task.sla")

SLA_LOOP_SECONDS = 30


async def run_once(sla: SlaService) -> None:
    warned = await sla.fire_once()
    if warned:
        log.info("sla.warned", count=warned)

# --------------------------------------------------------------------------
# Developed by 𝕏0L0™ (@davdxpx) | © 2026 XTV Network Global
# Don't Remove Credit
# Telegram Channel @XTVbots
# Developed for the 𝕏TV Network @XTVglobal
# Backup Channel @XTVhome
# Contact on Telegram @davdxpx
# --------------------------------------------------------------------------
