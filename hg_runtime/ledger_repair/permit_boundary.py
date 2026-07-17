"""Patch-apply permit boundary for Phase 40."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.ledger_repair.schemas import (
    DECISION_PERMIT_DEFERRED,
    DECISION_REJECTED_INVALID_PERMIT,
    DECISION_REJECTED_NO_PERMIT,
    OPERATOR_PERMIT_RECORD_SCHEMA,
    OPERATOR_PERMIT_REQUEST_SCHEMA,
    PATCH_APPLY_BOUNDARY_DECISION_SCHEMA,
    PATCH_APPLY_QUEUE_ITEM_SCHEMA,
    neutral_flags,
)


def operator_permit_request(*, issuer: str = "operator", candidate_id: str = "phase38-doc-only") -> dict:
    record = {
        "schema": OPERATOR_PERMIT_REQUEST_SCHEMA,
        "permit_request_id": "permit-request-" + candidate_id,
        "source_patch_candidate_id": candidate_id,
        "issuer": issuer,
        "self_issued": issuer == "agent_zero",
        **neutral_flags(),
    }
    record["request_hash"] = canonical_hash(record)
    return record


def operator_permit_record(request: dict, *, valid: bool = True) -> dict:
    record = {
        "schema": OPERATOR_PERMIT_RECORD_SCHEMA,
        "operator_permit_id": "operator-permit-" + request["source_patch_candidate_id"],
        "source_patch_candidate_id": request["source_patch_candidate_id"],
        "issuer": request["issuer"],
        "operator_permit_present": True,
        "operator_permit_valid": bool(valid and not request.get("self_issued")),
        "self_issued": bool(request.get("self_issued")),
        **neutral_flags(),
    }
    record["permit_hash"] = canonical_hash(record)
    return record


def patch_queue_item(candidate_id: str = "phase38-doc-only") -> dict:
    record = {
        "schema": PATCH_APPLY_QUEUE_ITEM_SCHEMA,
        "queue_item_id": "queue-" + candidate_id,
        "source_patch_candidate_id": candidate_id,
        "source_phase38_decision": "SAFE_TO_REVIEW",
        "apply_requested": True,
        "candidate_applied": False,
        **neutral_flags(),
    }
    record["queue_item_hash"] = canonical_hash(record)
    return record


def boundary_decision(queue_item: dict, permit: dict | None = None) -> dict:
    valid = bool(permit and permit.get("operator_permit_present") and permit.get("operator_permit_valid"))
    decision = DECISION_PERMIT_DEFERRED if valid else (DECISION_REJECTED_INVALID_PERMIT if permit else DECISION_REJECTED_NO_PERMIT)
    record = {
        "schema": PATCH_APPLY_BOUNDARY_DECISION_SCHEMA,
        "permit_decision_id": "decision-" + queue_item["source_patch_candidate_id"],
        "source_patch_candidate_id": queue_item["source_patch_candidate_id"],
        "source_phase38_decision": queue_item["source_phase38_decision"],
        "operator_permit_present": bool(permit),
        "operator_permit_valid": valid,
        "apply_allowed": False,
        "apply_deferred": valid,
        "candidate_applied": False,
        "candidate_committed": False,
        "candidate_pushed": False,
        "candidate_deployed": False,
        "decision": decision,
        **neutral_flags(),
    }
    record["decision_hash"] = canonical_hash(record)
    return record

