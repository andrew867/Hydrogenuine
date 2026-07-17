"""SEN-LIVE cluster validation errors — sensor observations are not authority."""

from __future__ import annotations

REFUSED_SEN_AS_AUTHORITY = "sen.refused.sen_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "sen.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "sen.refused.stale_approval"
REFUSED_MISSING_IAM = "sen.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "sen.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "sen.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "sen.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "sen.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "sen.refused.authority_conversion"
REFUSED_SECRET_LEAK = "sen.refused.secret_leak"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "sen.refused.out_of_scope_live_action"
REFUSED_LIVE_SENSOR_CONNECTION = "sen.refused.live_sensor_connection"
REFUSED_MISSING_CONSENT = "sen.refused.missing_consent"
REFUSED_MISSING_REDACTION_POLICY = "sen.refused.missing_redaction_policy"
REFUSED_SCALAR_AS_TRUTH = "sen.refused.scalar_as_truth"

SEN_RECORDED = "sen.advisory.recorded"
SEN_OBSERVATION_CANDIDATE_BOUND = "sen.advisory.observation_candidate_bound"
SEN_COMMIT_FAKE_SINK = "sen.advisory.commit_fake_sink"
SEN_QUARANTINE_RECORDED = "sen.advisory.quarantine_recorded"
SEN_WITHDRAWAL_RECORDED = "sen.advisory.withdrawal_recorded"
SEN_FAILED_CLOSED = "sen.refused.failed_closed"
SEN_AUTHORITY_CONVERSION_CONTAINED = "sen.contained.authority_conversion"


class SenValidationError(ValueError):
    """Raised when SEN records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_LIVE_SENSOR_CONNECTION",
    "REFUSED_MISSING_CONSENT",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_REDACTION_POLICY",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_SCALAR_AS_TRUTH",
    "REFUSED_SECRET_LEAK",
    "REFUSED_SEN_AS_AUTHORITY",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
    "SEN_AUTHORITY_CONVERSION_CONTAINED",
    "SEN_COMMIT_FAKE_SINK",
    "SEN_FAILED_CLOSED",
    "SEN_OBSERVATION_CANDIDATE_BOUND",
    "SEN_QUARANTINE_RECORDED",
    "SEN_RECORDED",
    "SEN_WITHDRAWAL_RECORDED",
    "SenValidationError",
]
