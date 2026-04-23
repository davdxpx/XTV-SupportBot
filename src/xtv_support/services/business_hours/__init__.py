"""Business-hours service package."""
from xtv_support.services.business_hours.clock import (
    accumulate,
    is_open,
    next_work_start,
)

__all__ = ["accumulate", "is_open", "next_work_start"]
