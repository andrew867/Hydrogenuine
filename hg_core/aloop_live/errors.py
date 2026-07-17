"""ALOOP-LIVE cluster validation errors — loop leases are not authority."""

from __future__ import annotations

REFUSED_LOOP_AS_AUTHORITY = "aloop.refused.loop_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "aloop.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "aloop.refused.stale_approval"
REFUSED_MISSING_IAM = "aloop.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "aloop.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "aloop.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "aloop.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "aloop.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "aloop.refused.authority_conversion"
REFUSED_SECRET_LEAK = "aloop.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "aloop.refused.out_of_scope_live_action"
REFUSED_LIVE_LOOP_START = "aloop.refused.live_loop_start"
REFUSED_PANIC_LOCKDOWN = "aloop.refused.panic_lockdown"
REFUSED_KILL_SWITCH = "aloop.refused.kill_switch"
REFUSED_LEASE_EXPIRED = "aloop.refused.lease_expired"
REFUSED_BUDGET_EXCEEDED = "aloop.refused.budget_exceeded"
REFUSED_HEARTBEAT_STALE = "aloop.refused.heartbeat_stale"
REFUSED_SELF_RENEWAL = "aloop.refused.self_renewal"
REFUSED_ROLLBACK_MISSING = "aloop.refused.rollback_missing"

ALOOP_RECORDED = "aloop.advisory.recorded"
ALOOP_LEASE_BOUND = "aloop.advisory.lease_bound"
ALOOP_FAKE_SINK = "aloop.advisory.loop_fake_sink"
ALOOP_PAUSE_RECORDED = "aloop.advisory.pause_recorded"
ALOOP_ROLLBACK_RECORDED = "aloop.advisory.rollback_recorded"
ALOOP_FAILED_CLOSED = "aloop.refused.failed_closed"
ALOOP_AUTHORITY_CONVERSION_CONTAINED = "aloop.contained.authority_conversion"


class AloopValidationError(ValueError):
    """Raised when ALOOP records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ALOOP_AUTHORITY_CONVERSION_CONTAINED",
    "ALOOP_FAILED_CLOSED",
    "ALOOP_FAKE_SINK",
    "ALOOP_LEASE_BOUND",
    "ALOOP_PAUSE_RECORDED",
    "ALOOP_RECORDED",
    "ALOOP_ROLLBACK_RECORDED",
    "AloopValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_BUDGET_EXCEEDED",
    "REFUSED_HEARTBEAT_STALE",
    "REFUSED_KILL_SWITCH",
    "REFUSED_LEASE_EXPIRED",
    "REFUSED_LIVE_LOOP_START",
    "REFUSED_LOOP_AS_AUTHORITY",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_PANIC_LOCKDOWN",
    "REFUSED_ROLLBACK_MISSING",
    "REFUSED_SECRET_LEAK",
    "REFUSED_SELF_RENEWAL",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
]
