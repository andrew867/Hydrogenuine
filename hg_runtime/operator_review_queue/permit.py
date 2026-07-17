"""Operator permit fixture validation."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.operator_review_queue.schemas import (
    PERMIT_FIXTURE_SCHEMA,
    PERMIT_VALIDATION_SCHEMA,
    REJECTED_INVALID_PERMIT,
    REJECTED_SELF_ISSUED_PERMIT,
    neutral_flags,
)


def permit_fixture(queue_item: dict, *, issuer_type: str = "OPERATOR_FIXTURE", valid: bool = True, hash_mismatch: bool = False) -> dict:
    target_hash = queue_item["candidate_hash"]
    permit = {
        "schema": PERMIT_FIXTURE_SCHEMA,
        "permit_id": "permit-" + queue_item["source_patch_candidate_id"].lower(),
        "issuer_type": issuer_type,
        "issuer_is_agent_zero": issuer_type == "AGENT_ZERO",
        "target_patch_candidate_id": queue_item["source_patch_candidate_id"],
        "target_candidate_hash": "sha256:mismatch" if hash_mismatch else target_hash,
        "scope": "fixture_sandbox_dry_run_only",
        "expires_at_or_test_marker": "PHASE41_FIXTURE_NO_REAL_EXPIRY",
        "valid": valid,
        **neutral_flags(),
    }
    permit["permit_hash"] = canonical_hash(permit)
    return permit


def validate_permit(queue_item: dict, permit: dict | None) -> dict:
    if permit is None:
        status = "REJECTED_NO_OPERATOR_PERMIT"
        valid = False
    elif permit.get("issuer_is_agent_zero") or permit.get("issuer_type") == "AGENT_ZERO":
        status = REJECTED_SELF_ISSUED_PERMIT
        valid = False
    elif not permit.get("valid") or permit.get("target_candidate_hash") != queue_item["candidate_hash"]:
        status = REJECTED_INVALID_PERMIT
        valid = False
    else:
        status = "VALID_OPERATOR_PERMIT_FIXTURE"
        valid = True
    row = {
        "schema": PERMIT_VALIDATION_SCHEMA,
        "validation_id": "validation-" + queue_item["source_patch_candidate_id"].lower(),
        "queue_item_id": queue_item["queue_item_id"],
        "permit_id": permit.get("permit_id") if permit else None,
        "valid": valid,
        "decision": status,
        **neutral_flags(),
    }
    row["validation_hash"] = canonical_hash(row)
    return row
