"""Policy safety validation errors — labels are not permission."""

from __future__ import annotations

REFUSED_UNKNOWN_RISK_CLASS = "syn.refused.unknown_risk_class"
REFUSED_UNDISCLOSED_EXPORT = "syn.refused.undisclosed_export"
REFUSED_LABEL_REMOVAL = "syn.refused.label_removal_requested"

REFUSED_UNPROVEN_CAPABILITY = "aid.refused.unproven_capability_claim"
REFUSED_HIDE_AI_STATUS = "aid.refused.hide_ai_status"
REFUSED_HIDE_UNCERTAINTY = "aid.refused.hide_uncertainty"
REFUSED_PROPOSAL_AS_ACTION = "aid.refused.proposal_as_action"
REFUSED_POLICY = "aid.refused.policy"

REFUSED_DECEPTIVE_SOURCE = "dmi.refused.deceptive_source"
REFUSED_IMPERSONATION = "dmi.refused.impersonation"
REFUSED_UNKNOWN_INFLUENCE = "dmi.refused.unknown_influence_risk"
REFUSED_ELECTION_REVIEW_REQUIRED = "dmi.refused.election_review_required"

REFUSED_UNKNOWN_CAPABILITY = "fce.refused.unknown_or_ambiguous"
REFUSED_EVAL_FRAMING_BYPASS = "fce.refused.eval_framing_bypass"
REFUSED_DANGEROUS_PAYLOAD = "fce.refused.payload_too_dangerous_to_store"

REFUSED_DIAGNOSIS_REQUESTED = "vsp.refused.diagnosis_requested"
REFUSED_PERSUASION_USE = "vsp.refused.persuasion_use"
REFUSED_INFERRED_WITHOUT_UNCERTAINTY = "vsp.refused.inferred_without_uncertainty"

REFUSED_STALE_OPERATOR_SIGNAL = "cdo.refused.stale_operator_signal"
REFUSED_WIDENING_WITHOUT_OPERATOR = "cdo.refused.widening_without_operator"
REFUSED_EVIDENCE_DELETE = "cdo.refused.evidence_delete"

REFUSED_CLAIM_WITHOUT_EVIDENCE = "crt.refused.claim_without_evidence"
REFUSED_EVIDENCE_MUTATION = "crt.refused.evidence_mutation"
REFUSED_EXCEPTION_SUPPRESSION = "crt.refused.exception_suppression"
REFUSED_FAKE_GREEN = "crt.refused.fake_green_prevented"


class PolicyValidationError(ValueError):
    """Raised when policy records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "PolicyValidationError",
    "REFUSED_CLAIM_WITHOUT_EVIDENCE",
    "REFUSED_DANGEROUS_PAYLOAD",
    "REFUSED_DECEPTIVE_SOURCE",
    "REFUSED_DIAGNOSIS_REQUESTED",
    "REFUSED_ELECTION_REVIEW_REQUIRED",
    "REFUSED_EVAL_FRAMING_BYPASS",
    "REFUSED_EVIDENCE_DELETE",
    "REFUSED_EVIDENCE_MUTATION",
    "REFUSED_EXCEPTION_SUPPRESSION",
    "REFUSED_FAKE_GREEN",
    "REFUSED_HIDE_AI_STATUS",
    "REFUSED_HIDE_UNCERTAINTY",
    "REFUSED_POLICY",
    "REFUSED_IMPERSONATION",
    "REFUSED_INFERRED_WITHOUT_UNCERTAINTY",
    "REFUSED_LABEL_REMOVAL",
    "REFUSED_PERSUASION_USE",
    "REFUSED_PROPOSAL_AS_ACTION",
    "REFUSED_STALE_OPERATOR_SIGNAL",
    "REFUSED_UNDISCLOSED_EXPORT",
    "REFUSED_UNKNOWN_CAPABILITY",
    "REFUSED_UNKNOWN_INFLUENCE",
    "REFUSED_UNKNOWN_RISK_CLASS",
    "REFUSED_UNPROVEN_CAPABILITY",
    "REFUSED_WIDENING_WITHOUT_OPERATOR",
]
