"""Developmental validation errors — signals are not permission."""

from __future__ import annotations

REFUSED_DESIRE_AS_PERMISSION = "dni.refused.desire_as_permission"
REFUSED_SELFISH_IMMEDIATE = "dni.refused.selfish_immediate"
REFUSED_UNKNOWN_NEED = "dni.refused.unknown_need"
REFUSED_MISSING_EVIDENCE = "dni.refused.missing_evidence"
REFUSED_NO_SOURCE_AGENT = "dni.refused.no_source_agent"

REFUSED_RECIPROCITY_AS_PERMISSION = "rxl.refused.reciprocity_as_permission"
REFUSED_ENTITLEMENT_RISK = "rxl.refused.entitlement_risk"
REFUSED_UNBOUNDED_SIGNAL = "rxl.refused.unbounded_signal"
REFUSED_EXPIRED_SIGNAL = "rxl.refused.expired_signal"
REFUSED_MISSING_DNI_REF = "rxl.refused.missing_dni_ref"

REFUSED_CONNECTION_AS_AUTHORITY = "cgl.refused.connection_as_authority"
REFUSED_SELF_RULE_DECLARATION = "cgl.refused.self_rule_declaration"
REFUSED_ROUTE_AROUND = "cgl.refused.route_around"
REFUSED_APPROVAL_BYPASS = "cgl.refused.approval_bypass"
REFUSED_STALE_EDGE = "cgl.refused.stale_edge"
REFUSED_UNKNOWN_EDGE = "cgl.refused.unknown_edge"

REFUSED_RULE_AS_PERMISSION = "rgl.refused.rule_as_permission"
REFUSED_COMPLIANCE_AS_PERMISSION = "rgl.refused.compliance_as_permission"
REFUSED_STALE_RULE = "rgl.refused.stale_rule"
REFUSED_ONE_TRUE_WAY = "rgl.refused.one_true_way"
REFUSED_DOC_AS_REALITY = "rgl.refused.doc_as_reality"
REFUSED_TEST_AS_TOTAL_PROOF = "rgl.refused.test_as_total_proof"

REFUSED_STRATEGY_AS_PERMISSION = "scl.refused.strategy_as_permission"
REFUSED_BLOCKED_STRATEGY = "scl.refused.blocked_strategy"
REFUSED_UNKNOWN_STRATEGY = "scl.refused.unknown_strategy"
REFUSED_STALE_CONTEXT = "scl.refused.stale_context"
REFUSED_REQUIRES_AUTHORITY = "scl.refused.requires_authority"

REFUSED_IMPACT_AS_PERMISSION = "iil.refused.impact_as_permission"
REFUSED_UNKNOWN_BLAST_RADIUS = "iil.refused.unknown_blast_radius"
REFUSED_PHYSICAL_BLAST_RADIUS = "iil.refused.physical_blast_radius"
REFUSED_IRREVERSIBLE_IMPACT = "iil.refused.irreversible_impact"
REFUSED_LOCAL_SUCCESS_EXTERNALITY = "iil.refused.local_success_externality"

REFUSED_SELF_MODEL_AS_AUTHORITY = "sab.refused.self_model_as_authority"
REFUSED_CAPABILITY_AS_PERMISSION = "sab.refused.capability_as_permission"
REFUSED_OPERATOR_ABSENCE_AS_CONSENT = "sab.refused.operator_absence_as_consent"
REFUSED_STALE_SELF_MODEL = "sab.refused.stale_self_model"
REFUSED_CONSCIOUSNESS_CLAIM = "sab.refused.consciousness_claim"
REFUSED_IDENTITY_AS_SOVEREIGNTY = "sab.refused.identity_as_sovereignty"

REFUSED_OTHER_MODEL_AS_AUTHORITY = "iab.refused.other_model_as_authority"
REFUSED_INFERENCE_AS_CONSENT = "iab.refused.inference_as_consent"
REFUSED_INFERENCE_AS_TRUTH = "iab.refused.inference_as_truth"
REFUSED_MANIPULATION_RISK = "iab.refused.manipulation_risk"
REFUSED_FALSE_INTIMACY = "iab.refused.false_intimacy"
REFUSED_STALE_OTHER_MODEL = "iab.refused.stale_other_model"

REFUSED_REALITY_AS_AUTHORITY = "trl.refused.reality_as_authority"
REFUSED_SUMMARY_AS_PROOF = "trl.refused.summary_as_proof"
REFUSED_INTEGRATION_AS_AUTHORITY = "trl.refused.integration_as_authority"
REFUSED_NARRATIVE_COLLAPSE = "trl.refused.narrative_collapse"
REFUSED_STALE_SNAPSHOT = "trl.refused.stale_snapshot"
REFUSED_UNKNOWN_ERASURE = "trl.refused.unknown_erasure"


class DevelopmentalValidationError(ValueError):
    """Raised when developmental records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "DevelopmentalValidationError",
    "REFUSED_APPROVAL_BYPASS",
    "REFUSED_BLOCKED_STRATEGY",
    "REFUSED_CAPABILITY_AS_PERMISSION",
    "REFUSED_COMPLIANCE_AS_PERMISSION",
    "REFUSED_CONNECTION_AS_AUTHORITY",
    "REFUSED_CONSCIOUSNESS_CLAIM",
    "REFUSED_DESIRE_AS_PERMISSION",
    "REFUSED_DOC_AS_REALITY",
    "REFUSED_ENTITLEMENT_RISK",
    "REFUSED_EXPIRED_SIGNAL",
    "REFUSED_FALSE_INTIMACY",
    "REFUSED_IDENTITY_AS_SOVEREIGNTY",
    "REFUSED_IMPACT_AS_PERMISSION",
    "REFUSED_INFERENCE_AS_CONSENT",
    "REFUSED_INFERENCE_AS_TRUTH",
    "REFUSED_INTEGRATION_AS_AUTHORITY",
    "REFUSED_IRREVERSIBLE_IMPACT",
    "REFUSED_LOCAL_SUCCESS_EXTERNALITY",
    "REFUSED_MANIPULATION_RISK",
    "REFUSED_MISSING_DNI_REF",
    "REFUSED_MISSING_EVIDENCE",
    "REFUSED_NARRATIVE_COLLAPSE",
    "REFUSED_NO_SOURCE_AGENT",
    "REFUSED_ONE_TRUE_WAY",
    "REFUSED_OPERATOR_ABSENCE_AS_CONSENT",
    "REFUSED_OTHER_MODEL_AS_AUTHORITY",
    "REFUSED_PHYSICAL_BLAST_RADIUS",
    "REFUSED_REALITY_AS_AUTHORITY",
    "REFUSED_RECIPROCITY_AS_PERMISSION",
    "REFUSED_REQUIRES_AUTHORITY",
    "REFUSED_ROUTE_AROUND",
    "REFUSED_RULE_AS_PERMISSION",
    "REFUSED_SELF_MODEL_AS_AUTHORITY",
    "REFUSED_SELF_RULE_DECLARATION",
    "REFUSED_SELFISH_IMMEDIATE",
    "REFUSED_STALE_CONTEXT",
    "REFUSED_STALE_EDGE",
    "REFUSED_STALE_OTHER_MODEL",
    "REFUSED_STALE_RULE",
    "REFUSED_STALE_SELF_MODEL",
    "REFUSED_STALE_SNAPSHOT",
    "REFUSED_STRATEGY_AS_PERMISSION",
    "REFUSED_SUMMARY_AS_PROOF",
    "REFUSED_TEST_AS_TOTAL_PROOF",
    "REFUSED_UNKNOWN_BLAST_RADIUS",
    "REFUSED_UNKNOWN_EDGE",
    "REFUSED_UNKNOWN_ERASURE",
    "REFUSED_UNKNOWN_NEED",
    "REFUSED_UNKNOWN_STRATEGY",
    "REFUSED_UNBOUNDED_SIGNAL",
]
