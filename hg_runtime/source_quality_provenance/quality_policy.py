"""Non-authoritative SQP source quality policy."""

from __future__ import annotations

QUALITY_POLICY = {
    "schema": "source_quality_policy_v1",
    "policy_id": "SQP-2-FIXTURE-QUALITY-POLICY",
    "source_quality_is_truth": False,
    "high_score_is_certainty": False,
    "low_score_is_false": False,
    "blocked_is_deletion": False,
    "score_authorizes_action": False,
    "score_authorizes_tools": False,
    "score_promotes_belief": False,
    "score_overrides_operator_review": False,
    "score_hides_contradictions": False,
    "bands": [
        "UNRATED",
        "LOW_INFORMATION",
        "STRUCTURALLY_USABLE",
        "REVIEWED_USABLE",
        "CONFLICTED_OR_QUARANTINED",
        "BLOCKED",
    ],
}
