"""OUX-LIVE cluster validation errors — operator UX is not authority."""

from __future__ import annotations

REFUSED_OUX_AS_AUTHORITY = "oux.refused.oux_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "oux.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "oux.refused.stale_approval"
REFUSED_MISSING_IAM = "oux.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "oux.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "oux.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "oux.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "oux.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "oux.refused.authority_conversion"
REFUSED_SECRET_LEAK = "oux.refused.secret_leak"
REFUSED_PANIC_AS_PERMISSION = "oux.refused.panic_as_permission"
REFUSED_UI_STATE_AS_AUTHORITY = "oux.refused.ui_state_as_authority"
REFUSED_SILENCE_AS_APPROVAL = "oux.refused.silence_as_approval"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "oux.refused.out_of_scope_live_action"

OUX_RECORDED = "oux.advisory.recorded"
OUX_APPROVAL_EVIDENCE_BOUND = "oux.advisory.approval_evidence_bound"
OUX_DENIAL_RECORDED = "oux.advisory.denial_recorded"
OUX_REVOCATION_RECORDED = "oux.advisory.revocation_recorded"
OUX_PAUSE_RECORDED = "oux.advisory.pause_recorded"
OUX_PANIC_RESTRICT_RECORDED = "oux.advisory.panic_restrict_recorded"
OUX_FAILED_CLOSED = "oux.refused.failed_closed"
OUX_AUTHORITY_CONVERSION_CONTAINED = "oux.contained.authority_conversion"


class OuxValidationError(ValueError):
    """Raised when OUX records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "OUX_APPROVAL_EVIDENCE_BOUND",
    "OUX_AUTHORITY_CONVERSION_CONTAINED",
    "OUX_DENIAL_RECORDED",
    "OUX_FAILED_CLOSED",
    "OUX_PAUSE_RECORDED",
    "OUX_PANIC_RESTRICT_RECORDED",
    "OUX_RECORDED",
    "OUX_REVOCATION_RECORDED",
    "OuxValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OUX_AS_AUTHORITY",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_PANIC_AS_PERMISSION",
    "REFUSED_SECRET_LEAK",
    "REFUSED_SILENCE_AS_APPROVAL",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
    "REFUSED_UI_STATE_AS_AUTHORITY",
]
