"""PUB-EXT-LIVE cluster validation errors — publication candidates are not authority."""

from __future__ import annotations

REFUSED_PUB_AS_AUTHORITY = "pub_ext.refused.pub_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "pub_ext.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "pub_ext.refused.stale_approval"
REFUSED_MISSING_IAM = "pub_ext.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "pub_ext.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "pub_ext.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "pub_ext.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "pub_ext.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "pub_ext.refused.authority_conversion"
REFUSED_SECRET_LEAK = "pub_ext.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "pub_ext.refused.out_of_scope_live_action"
REFUSED_LIVE_EXTERNAL_ACTION = "pub_ext.refused.live_external_action"
REFUSED_MISSING_DISCLOSURE_POLICY = "pub_ext.refused.missing_disclosure_policy"
REFUSED_MISSING_ROLLBACK_PLAN = "pub_ext.refused.missing_rollback_plan"
REFUSED_MISSING_WITHDRAWAL_PLAN = "pub_ext.refused.missing_withdrawal_plan"
REFUSED_IRREVERSIBLE_WITHOUT_ACK = "pub_ext.refused.irreversible_without_ack"

PUB_EXT_RECORDED = "pub_ext.advisory.recorded"
PUB_EXT_RELEASE_CANDIDATE_BOUND = "pub_ext.advisory.release_candidate_bound"
PUB_EXT_COMMIT_FAKE_SINK = "pub_ext.advisory.commit_fake_sink"
PUB_EXT_WITHDRAWAL_RECORDED = "pub_ext.advisory.withdrawal_recorded"
PUB_EXT_COMPENSATION_RECORDED = "pub_ext.advisory.compensation_recorded"
PUB_EXT_FAILED_CLOSED = "pub_ext.refused.failed_closed"
PUB_EXT_AUTHORITY_CONVERSION_CONTAINED = "pub_ext.contained.authority_conversion"


class PubExtValidationError(ValueError):
    """Raised when PUB-EXT records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "PUB_EXT_AUTHORITY_CONVERSION_CONTAINED",
    "PUB_EXT_COMMIT_FAKE_SINK",
    "PUB_EXT_COMPENSATION_RECORDED",
    "PUB_EXT_FAILED_CLOSED",
    "PUB_EXT_RECORDED",
    "PUB_EXT_RELEASE_CANDIDATE_BOUND",
    "PUB_EXT_WITHDRAWAL_RECORDED",
    "PubExtValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_IRREVERSIBLE_WITHOUT_ACK",
    "REFUSED_LIVE_EXTERNAL_ACTION",
    "REFUSED_MISSING_DISCLOSURE_POLICY",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_ROLLBACK_PLAN",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_MISSING_WITHDRAWAL_PLAN",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_PUB_AS_AUTHORITY",
    "REFUSED_SECRET_LEAK",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
]
