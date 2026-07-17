"""Contradiction type constants and severity levels.

Contradiction is not a truth decision. Model consensus is not proof.
"""

from __future__ import annotations

CONTRADICTION_TYPES = {
    "source_vs_source",
    "model_vs_model",
    "persona_vs_persona",
    "model_vs_source",
    "source_vs_memory",
    "claim_vs_boundary",
    "evidence_gap_vs_claim",
    "falsification_target_vs_claim",
    "consensus_without_evidence",
    "disagreement_without_resolution",
}

RESOLUTION_STATES = {
    "unresolved",
    "needs_source",
    "needs_operator",
    "resolved_as_scope_difference",
    "rejected_overclaim",
}

SEVERITY_LEVELS = {"critical", "high", "medium", "low", "info"}
