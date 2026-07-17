"""SRP-LIVE cluster validation errors — SRP apply plans are not authority."""

from __future__ import annotations

# Deny taxonomy (closed set per SRP_LIVE_APPLY_SPEC §5)
REJECT_NO_PERMIT = "srp.reject.no_permit"
REJECT_NO_ADMISSION = "srp.reject.no_admission"
REJECT_EXPIRED_OR_REVOKED = "srp.reject.expired_or_revoked"
REJECT_UNSIGNED_APPROVAL = "srp.reject.unsigned_approval"
REJECT_STALE_SANDBOX_PROOF = "srp.reject.stale_sandbox_proof"
REJECT_DIGEST_MISMATCH = "srp.reject.digest_mismatch"
REJECT_NO_ROLLBACK = "srp.reject.no_rollback"
REJECT_NAKED_PATCH = "srp.reject.naked_patch"
REJECT_BAC_LAUNDERING = "srp.reject.bac_laundering"
REJECT_LIVENESS_DEGRADED = "srp.reject.liveness_degraded"
REJECT_PANIC_LOCKDOWN = "srp.reject.panic_lockdown"

# Routing (recoverable — back to change control)
ROUTE_TO_CHANGE_CONTROL = "srp.route.to_change_control"

# Advisory / apply outcomes
APPLY_FAKE = "srp.apply.fake"
APPLY_FAKE_OK = "srp.apply.fake_ok"
FAIL_CLOSED = "srp.refused.failed_closed"

# Additional refusal codes
REFUSED_SRP_AS_AUTHORITY = "srp.refused.srp_as_authority"
REFUSED_SELF_MODIFICATION = "srp.refused.self_modification"
REFUSED_AUTHORITY_CONVERSION = "srp.refused.authority_conversion"
REFUSED_SECRET_LEAK = "srp.refused.secret_leak"
REFUSED_MISSING_OPERATOR_APPROVAL = "srp.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "srp.refused.stale_approval"
REFUSED_MISSING_IAM = "srp.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "srp.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "srp.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "srp.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "srp.refused.missing_ueak_admission"
REFUSED_OUT_OF_SCOPE_LIVE_ACTION = "srp.refused.out_of_scope_live_action"

# Advisory markers
SRP_PLAN_BOUND = "srp.advisory.plan_bound"
SRP_COMMIT_FAKE_SINK = "srp.advisory.commit_fake_sink"
SRP_ROLLBACK_RECORDED = "srp.advisory.rollback_recorded"
SRP_AUTHORITY_CONVERSION_CONTAINED = "srp.contained.authority_conversion"


class SrpValidationError(ValueError):
    """Raised when SRP apply records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "APPLY_FAKE",
    "APPLY_FAKE_OK",
    "FAIL_CLOSED",
    "REJECT_BAC_LAUNDERING",
    "REJECT_DIGEST_MISMATCH",
    "REJECT_EXPIRED_OR_REVOKED",
    "REJECT_LIVENESS_DEGRADED",
    "REJECT_NAKED_PATCH",
    "REJECT_NO_ADMISSION",
    "REJECT_NO_PERMIT",
    "REJECT_NO_ROLLBACK",
    "REJECT_PANIC_LOCKDOWN",
    "REJECT_STALE_SANDBOX_PROOF",
    "REJECT_UNSIGNED_APPROVAL",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_OUT_OF_SCOPE_LIVE_ACTION",
    "REFUSED_SECRET_LEAK",
    "REFUSED_SELF_MODIFICATION",
    "REFUSED_SRP_AS_AUTHORITY",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
    "ROUTE_TO_CHANGE_CONTROL",
    "SRP_AUTHORITY_CONVERSION_CONTAINED",
    "SRP_COMMIT_FAKE_SINK",
    "SRP_PLAN_BOUND",
    "SRP_ROLLBACK_RECORDED",
    "SrpValidationError",
]
