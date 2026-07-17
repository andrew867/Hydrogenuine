"""Maintenance policy receipt — bounded audit maintenance doctrine."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    AUDIT_CLOSURE_IS_NOT_LAUNDERING,
    DECAY_IS_NOT_DELETION,
    MAINTENANCE_POLICY_SCHEMA,
    RETRACTION_IS_NOT_ERASURE,
    SOURCE_PHASE_ID,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_maintenance_policy() -> dict:
    policy = {
        "schema": MAINTENANCE_POLICY_SCHEMA,
        "policy_id": "wmbr06-maintenance-policy",
        "source_phase": SOURCE_PHASE_ID,
        "decay_is_not_deletion": True,
        "retraction_is_not_erasure": True,
        "audit_closure_is_not_laundering": True,
        "stale_records_remain_visible": True,
        "failed_predictions_remain_visible": True,
        "contradictions_remain_visible": True,
        "automatic_deletion_allowed": False,
        "automatic_patching_allowed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "doctrine_statements": [
            DECAY_IS_NOT_DELETION,
            RETRACTION_IS_NOT_ERASURE,
            AUDIT_CLOSURE_IS_NOT_LAUNDERING,
        ],
        **neutral_flags(),
    }
    policy["policy_hash"] = canonical_hash(policy)
    assert_neutral(policy)
    return policy


def validate_maintenance_policy(policy: dict) -> None:
    if policy.get("schema") != MAINTENANCE_POLICY_SCHEMA:
        raise ValueError("invalid_maintenance_policy_schema")
    if policy.get("automatic_deletion_allowed") or policy.get("decay_treated_as_deletion"):
        raise ValueError("automatic_deletion_forbidden")
    assert_neutral(policy)
