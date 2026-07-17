"""Evidence Graph schema constants.

Edges are NOT proof. Citation is NOT truth. Source candidates are NOT evidence.
Model output is NOT evidence. The graph is a structural aid for operator review,
not an authority mechanism.

Promotion is NEVER allowed. Operator review is ALWAYS required.
"""

from __future__ import annotations

SCHEMA_VERSION = "evidence_graph_v1"

NODE_TYPES = {
    "seed", "claim", "source_candidate", "source_receipt",
    "model_output_receipt", "quality_review", "contradiction",
    "evidence_gap", "falsification_target", "uncertainty_record",
    "memory_candidate", "operator_review", "promotion_decision",
}

EDGE_TYPES = {
    "seed_generated_claim", "claim_supported_by_source_candidate",
    "claim_contradicted_by_source", "claim_has_evidence_gap",
    "claim_has_falsification_target", "claim_from_model_output",
    "claim_reviewed_by_quality_gate", "claim_in_contradiction",
    "claim_quarantined_as_memory_candidate", "operator_review_required_for",
    "promotion_rejected", "promotion_deferred", "promotion_approved_by_gate",
}

_INVARIANTS = {
    "graph_edge_is_not_proof": True,
    "citation_is_not_truth": True,
    "source_candidate_is_not_evidence": True,
    "model_output_is_not_evidence": True,
    "promotion_allowed": False,
    "operator_review_required": True,
    "model_output_treated_as_truth": False,
}
