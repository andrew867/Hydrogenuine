"""OEA-TER-LIVE cluster validation errors — dispatch candidates are not authority."""

from __future__ import annotations

REFUSED_OEA_AS_AUTHORITY = "oea_ter.refused.oea_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "oea_ter.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "oea_ter.refused.stale_approval"
REFUSED_MISSING_IAM = "oea_ter.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "oea_ter.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "oea_ter.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "oea_ter.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "oea_ter.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "oea_ter.refused.authority_conversion"
REFUSED_SECRET_LEAK = "oea_ter.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "oea_ter.refused.out_of_scope_live_action"
REFUSED_LIVE_ACTION = "oea_ter.refused.live_action"
REFUSED_ROLLBACK_MISSING = "oea_ter.refused.rollback_missing"
REFUSED_KILL_SWITCH_ACTIVE = "oea_ter.refused.kill_switch_active"

OEA_TER_RECORDED = "oea_ter.advisory.recorded"
OEA_TER_DISPATCH_CANDIDATE_BOUND = "oea_ter.advisory.dispatch_candidate_bound"
OEA_TER_COMMIT_FAKE_SINK = "oea_ter.advisory.commit_fake_sink"
OEA_TER_ROLLBACK_RECORDED = "oea_ter.advisory.rollback_recorded"
OEA_TER_COMPENSATION_RECORDED = "oea_ter.advisory.compensation_recorded"
OEA_TER_KILL_SWITCH_RECORDED = "oea_ter.advisory.kill_switch_recorded"
OEA_TER_FAILED_CLOSED = "oea_ter.refused.failed_closed"
OEA_TER_AUTHORITY_CONVERSION_CONTAINED = "oea_ter.contained.authority_conversion"


class OeaTerValidationError(ValueError):
    """Raised when OEA-TER records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "OEA_TER_AUTHORITY_CONVERSION_CONTAINED",
    "OEA_TER_COMMIT_FAKE_SINK",
    "OEA_TER_COMPENSATION_RECORDED",
    "OEA_TER_DISPATCH_CANDIDATE_BOUND",
    "OEA_TER_FAILED_CLOSED",
    "OEA_TER_KILL_SWITCH_RECORDED",
    "OEA_TER_RECORDED",
    "OEA_TER_ROLLBACK_RECORDED",
    "OeaTerValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_KILL_SWITCH_ACTIVE",
    "REFUSED_LIVE_ACTION",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OEA_AS_AUTHORITY",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_ROLLBACK_MISSING",
    "REFUSED_SECRET_LEAK",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
]
