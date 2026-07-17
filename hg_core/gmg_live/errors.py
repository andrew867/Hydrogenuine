"""GMG-LIVE cluster validation errors — grant candidates are not authority."""

from __future__ import annotations

REFUSED_GRANT_AS_AUTHORITY = "gmg.refused.grant_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "gmg.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "gmg.refused.stale_approval"
REFUSED_MISSING_IAM = "gmg.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "gmg.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "gmg.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "gmg.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "gmg.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "gmg.refused.authority_conversion"
REFUSED_SECRET_LEAK = "gmg.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "gmg.refused.out_of_scope_live_action"
REFUSED_LIVE_GRANT = "gmg.refused.live_grant"
REFUSED_ROLLBACK_MISSING = "gmg.refused.rollback_missing"
REFUSED_AMBIENT_GRANT = "gmg.refused.ambient_grant"
REFUSED_EXPIRED_GRANT = "gmg.refused.expired_grant"
REFUSED_MISSING_GRANT_TARGET = "gmg.refused.missing_grant_target"

GMG_RECORDED = "gmg.advisory.recorded"
GMG_GRANT_CANDIDATE_BOUND = "gmg.advisory.grant_candidate_bound"
GMG_COMMIT_FAKE_SINK = "gmg.advisory.commit_fake_sink"
GMG_REVOCATION_RECORDED = "gmg.advisory.revocation_recorded"
GMG_EXPIRY_RECORDED = "gmg.advisory.expiry_recorded"
GMG_FAILED_CLOSED = "gmg.refused.failed_closed"
GMG_AUTHORITY_CONVERSION_CONTAINED = "gmg.contained.authority_conversion"


class GmgValidationError(ValueError):
    """Raised when GMG records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "GMG_AUTHORITY_CONVERSION_CONTAINED",
    "GMG_COMMIT_FAKE_SINK",
    "GMG_EXPIRY_RECORDED",
    "GMG_FAILED_CLOSED",
    "GMG_GRANT_CANDIDATE_BOUND",
    "GMG_RECORDED",
    "GMG_REVOCATION_RECORDED",
    "GmgValidationError",
    "REFUSED_AMBIENT_GRANT",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_EXPIRED_GRANT",
    "REFUSED_GRANT_AS_AUTHORITY",
    "REFUSED_LIVE_GRANT",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_GRANT_TARGET",
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
