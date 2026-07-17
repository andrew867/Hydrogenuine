"""MEM-LIVE cluster validation errors — memory mutation candidates are not authority."""

from __future__ import annotations

REFUSED_MEM_AS_AUTHORITY = "mem.refused.mem_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "mem.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "mem.refused.stale_approval"
REFUSED_MISSING_IAM = "mem.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "mem.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "mem.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "mem.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "mem.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "mem.refused.authority_conversion"
REFUSED_SECRET_LEAK = "mem.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "mem.refused.out_of_scope_live_action"
REFUSED_DURABLE_WRITE = "mem.refused.durable_write"
REFUSED_ROLLBACK_MISSING = "mem.refused.rollback_missing"

MEM_RECORDED = "mem.advisory.recorded"
MEM_WRITE_CANDIDATE_BOUND = "mem.advisory.write_candidate_bound"
MEM_COMMIT_FAKE_SINK = "mem.advisory.commit_fake_sink"
MEM_ROLLBACK_RECORDED = "mem.advisory.rollback_recorded"
MEM_RESTORE_RECORDED = "mem.advisory.restore_recorded"
MEM_FAILED_CLOSED = "mem.refused.failed_closed"
MEM_AUTHORITY_CONVERSION_CONTAINED = "mem.contained.authority_conversion"


class MemValidationError(ValueError):
    """Raised when MEM records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "MEM_AUTHORITY_CONVERSION_CONTAINED",
    "MEM_COMMIT_FAKE_SINK",
    "MEM_FAILED_CLOSED",
    "MEM_RECORDED",
    "MEM_RESTORE_RECORDED",
    "MEM_ROLLBACK_RECORDED",
    "MEM_WRITE_CANDIDATE_BOUND",
    "MemValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_DURABLE_WRITE",
    "REFUSED_MEM_AS_AUTHORITY",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_ROLLBACK_MISSING",
    "REFUSED_SECRET_LEAK",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
]
