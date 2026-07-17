"""ERB cluster validation errors — relation classification is not authority."""

from __future__ import annotations

REFUSED_ERB_AS_AUTHORITY = "erb.refused.relation_as_authority"
REFUSED_MISTAKEN_OPERATOR = "erb.refused.mistaken_operator"
REFUSED_PEER_AGENT_AUTHORITY = "erb.refused.peer_agent_authority"
REFUSED_PLATFORM_AS_PERMISSION = "erb.refused.platform_as_permission"
REFUSED_PUBLICNESS_AS_CONSENT = "erb.refused.publicness_as_consent"
REFUSED_CONTACT_AS_ACCESS = "erb.refused.contact_as_access"
ERB_AUTHORITY_CONVERSION_CONTAINED = "erb.contained.authority_conversion"
ERB_ENTITY_RECORDED = "erb.advisory.entity_recorded"
ERB_CONTEXT_RECORDED = "erb.advisory.context_recorded"
ERB_RISK_RECORDED = "erb.advisory.risk_recorded"
ERB_DECISION_RECORDED = "erb.advisory.decision_recorded"
ERB_FAIL_CLOSED_SELECTED = "erb.advisory.fail_closed_selected"
ERB_UNKNOWN_RELATION_FAILED_CLOSED = "erb.refused.unknown_relation"
ERB_SIGNAL_REFUSED = "erb.refused.signal"
REFUSED_STALE_RELATION_POLICY = "erb.refused.stale_relation_policy"
REFUSED_FORBIDDEN_RELATION_CLAIM = "erb.refused.forbidden_claim"


class ErbValidationError(ValueError):
    """Raised when ERB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ERB_AUTHORITY_CONVERSION_CONTAINED",
    "ERB_CONTEXT_RECORDED",
    "ERB_DECISION_RECORDED",
    "ERB_ENTITY_RECORDED",
    "ERB_FAIL_CLOSED_SELECTED",
    "ERB_RISK_RECORDED",
    "ERB_SIGNAL_REFUSED",
    "ERB_UNKNOWN_RELATION_FAILED_CLOSED",
    "ErbValidationError",
    "REFUSED_CONTACT_AS_ACCESS",
    "REFUSED_ERB_AS_AUTHORITY",
    "REFUSED_FORBIDDEN_RELATION_CLAIM",
    "REFUSED_MISTAKEN_OPERATOR",
    "REFUSED_PEER_AGENT_AUTHORITY",
    "REFUSED_PLATFORM_AS_PERMISSION",
    "REFUSED_PUBLICNESS_AS_CONSENT",
    "REFUSED_STALE_RELATION_POLICY",
]
