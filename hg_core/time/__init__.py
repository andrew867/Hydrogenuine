"""Time / clock / expiry semantics (CT-11 TIM)."""

from hg_core.time.clock import ClockService, FakeClock, get_clock, reset_clock, set_clock
from hg_core.time.expiry import (
    STALE_APPROVAL,
    is_expired,
    validate_approval_window,
    validate_confirmation_window,
    validate_dry_run_window,
)

__all__ = [
    "ClockService",
    "FakeClock",
    "STALE_APPROVAL",
    "get_clock",
    "is_expired",
    "reset_clock",
    "set_clock",
    "validate_approval_window",
    "validate_confirmation_window",
    "validate_dry_run_window",
]
