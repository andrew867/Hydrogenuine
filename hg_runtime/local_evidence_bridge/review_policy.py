"""LEB-5 evidence review policy.

Defines what local evidence receipts and LEB outputs require operator review, and
how active fever restricts (never unlocks) the review flow. A review task is never
an action, a belief promotion, a tool authorization, or an operator approval.
"""

from __future__ import annotations

from hg_runtime.agent_immune_system.restriction_policy import restrictions_for_level
from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)

RESTRICTING_FEVER_LEVELS = ("RED_FEVER", "PANIC_FEVER")
# Target record kinds that always require review.
ALWAYS_REVIEW_KINDS = (
    "evidence_contradiction_record_v1",
    "local_evidence_contradiction_v1",
)


def build_review_policy(*, fever_level: str = "NORMAL") -> dict:
    restrictions = restrictions_for_level(fever_level)
    review_flow_restricted = fever_level in RESTRICTING_FEVER_LEVELS
    policy = {
        "schema_version": "1",
        "record_type": "evidence_review_policy_v1",
        "policy_id": "leb5-evidence-review-policy",
        "fever_level": fever_level,
        "review_flow_restricted": review_flow_restricted,
        "restrictions": restrictions,
        "review_required_for_contradictions": True,
        "review_required_for_redaction_flagged": True,
        "suspicious_recommends_quarantine_candidate": True,
        "review_task_is_action": False,
        "review_task_is_belief_promotion": False,
        "review_task_is_operator_approval": False,
        "review_task_is_tool_authorization": False,
        "automatic_patching_enabled": False,
        "deletion_enabled": False,
        "fever_unlocks_action": False,
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy


def classify_target(record: dict) -> tuple[str, str]:
    """Return (recommended_action, reason) for a target record.

    Suspicious targets (redaction-flagged or contradiction) recommend a
    quarantine *candidate* (metadata only — never deletion). Everything else
    recommends ordinary operator review.
    """
    kind = record.get("record_type", "unknown")
    if record.get("secret_like_content_redacted"):
        return "QUARANTINE_CANDIDATE", "redaction_flagged_suspicious"
    if kind in ALWAYS_REVIEW_KINDS or record.get("link_kind") == "CONTRADICTION_CANDIDATE":
        return "QUARANTINE_CANDIDATE", "contradiction_requires_review"
    if record.get("review_required"):
        return "OPERATOR_REVIEW", "review_required_flag"
    return "OPERATOR_REVIEW", "default_review"
