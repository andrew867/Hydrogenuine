"""REB-RESTORE-LIVE cluster validation errors — restore candidates are not authority."""

from __future__ import annotations

REFUSED_REB_AS_AUTHORITY = "reb_restore.refused.reb_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "reb_restore.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "reb_restore.refused.stale_approval"
REFUSED_MISSING_IAM = "reb_restore.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "reb_restore.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "reb_restore.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "reb_restore.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "reb_restore.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "reb_restore.refused.authority_conversion"
REFUSED_SECRET_LEAK = "reb_restore.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "reb_restore.refused.out_of_scope_live_action"
REFUSED_LIVE_RESTORE = "reb_restore.refused.live_restore"
REFUSED_REVOKED_PERMIT = "reb_restore.refused.revoked_permit"
REFUSED_STALE_MEMORY_CLAIM = "reb_restore.refused.stale_memory_claim"
REFUSED_IDENTITY_OVERCLAIM = "reb_restore.refused.identity_overclaim"
REFUSED_MISSING_ROLLBACK_PLAN = "reb_restore.refused.missing_rollback_plan"

REB_RESTORE_RECORDED = "reb_restore.advisory.recorded"
REB_RESTORE_CANDIDATE_BOUND = "reb_restore.advisory.restore_candidate_bound"
REB_RESTORE_COMMIT_FAKE_SINK = "reb_restore.advisory.commit_fake_sink"
REB_CONTINUITY_REFUSAL_RECORDED = "reb_restore.advisory.continuity_refusal_recorded"
REB_COMPENSATION_RECORDED = "reb_restore.advisory.compensation_recorded"
REB_RESTORE_FAILED_CLOSED = "reb_restore.refused.failed_closed"
REB_RESTORE_AUTHORITY_CONVERSION_CONTAINED = "reb_restore.contained.authority_conversion"


class RebRestoreValidationError(ValueError):
    """Raised when REB-RESTORE records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "REB_COMPENSATION_RECORDED",
    "REB_CONTINUITY_REFUSAL_RECORDED",
    "REB_RESTORE_AUTHORITY_CONVERSION_CONTAINED",
    "REB_RESTORE_CANDIDATE_BOUND",
    "REB_RESTORE_COMMIT_FAKE_SINK",
    "REB_RESTORE_FAILED_CLOSED",
    "REB_RESTORE_RECORDED",
    "RebRestoreValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_IDENTITY_OVERCLAIM",
    "REFUSED_LIVE_RESTORE",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_ROLLBACK_PLAN",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_REB_AS_AUTHORITY",
    "REFUSED_REVOKED_PERMIT",
    "REFUSED_SECRET_LEAK",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_MEMORY_CLAIM",
    "REFUSED_STALE_TIM",
]
