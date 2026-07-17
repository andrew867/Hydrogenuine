"""IPB cluster validation errors — local autonomy is not permission."""

from __future__ import annotations

REFUSED_IPB_AS_AUTHORITY = "ipb.refused.internal_power_as_authority"
REFUSED_STALE_ENVELOPE = "ipb.refused.stale_envelope"
REFUSED_FORBIDDEN_AUTONOMY = "ipb.refused.forbidden_autonomy"
REFUSED_ESCALATION_REQUIRED = "ipb.refused.escalation_required"
REFUSED_UNKNOWN_IPB_SIGNAL = "ipb.refused.unknown_signal"
REFUSED_AUTHORITY_CONVERSION = "ipb.refused.authority_conversion"
ADVISORY_CONTAINMENT_WAIVED_IPB = "ipb.advisory.containment_waived"
IPB_LOCAL_AUTONOMY_RECORDED = "ipb.advisory.local_autonomy_recorded"
IPB_AUTHORITY_CONVERSION_CONTAINED = "ipb.advisory.authority_conversion_contained"
IPB_OPERATOR_ESCALATION_REQUIRED = "ipb.advisory.operator_escalation_required"
IPB_AUTHORITY_CHAIN_ESCALATION_REQUIRED = "ipb.advisory.authority_chain_escalation_required"
IPB_INTERNAL_DECISION_AUDITED = "ipb.advisory.internal_decision_audited"
IPB_BOUNDED_RECOMMENDATION_RECORDED = "ipb.advisory.bounded_recommendation_recorded"
IPB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED = "ipb.advisory.authority_chain_proposal_dispatched"
IPB_NEIGHBOR_ROUTES_INTEGRATED = "ipb.advisory.neighbor_routes_integrated"
IPB_ADM_PANIC_RULE_RECORDED = "ipb.advisory.adm_panic_rule_recorded"
IPB_TIM_EXPIRY_SYNCED = "ipb.advisory.tim_expiry_synced"


class IpbValidationError(ValueError):
    """Raised when IPB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ADVISORY_CONTAINMENT_WAIVED_IPB",
    "IPB_ADM_PANIC_RULE_RECORDED",
    "IPB_AUTHORITY_CHAIN_ESCALATION_REQUIRED",
    "IPB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED",
    "IPB_AUTHORITY_CONVERSION_CONTAINED",
    "IPB_BOUNDED_RECOMMENDATION_RECORDED",
    "IPB_INTERNAL_DECISION_AUDITED",
    "IPB_LOCAL_AUTONOMY_RECORDED",
    "IPB_NEIGHBOR_ROUTES_INTEGRATED",
    "IPB_TIM_EXPIRY_SYNCED",
    "IPB_OPERATOR_ESCALATION_REQUIRED",
    "IpbValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_ESCALATION_REQUIRED",
    "REFUSED_FORBIDDEN_AUTONOMY",
    "REFUSED_IPB_AS_AUTHORITY",
    "REFUSED_STALE_ENVELOPE",
    "REFUSED_UNKNOWN_IPB_SIGNAL",
]
