"""LEB-7 evidence retention policy.

Defines how bad/suspect/stale/contradicted/redaction-failed local evidence is
handled. The policy is append-only and never deletes: retraction, quarantine, and
decay are all metadata operations that preserve the original receipt.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)

# Conditions that require a retraction record.
RETRACTABLE_CONDITIONS = ("BAD", "SUSPECT", "STALE", "CONTRADICTED", "REDACTION_FAILED")
# Conditions that additionally produce a quarantine record (vs. decay).
QUARANTINE_CONDITIONS = ("BAD", "SUSPECT", "CONTRADICTED", "REDACTION_FAILED")
DECAY_CONDITIONS = ("STALE",)


def build_retention_policy() -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "evidence_retention_policy_v1",
        "policy_id": "leb7-evidence-retention-policy",
        "retractable_conditions": list(RETRACTABLE_CONDITIONS),
        "quarantine_conditions": list(QUARANTINE_CONDITIONS),
        "decay_conditions": list(DECAY_CONDITIONS),
        "append_only": True,
        "deletion_enabled": False,
        "erasure_enabled": False,
        "original_receipt_always_preserved": True,
        "retraction_creates_review_requirement": True,
        "derived_belief_revisions_remain_auditable": True,
        "automatic_patching_enabled": False,
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy
