"""Append-only ledger repair records."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.ledger_repair.schemas import (
    LEDGER_REPAIR_RECORD_SCHEMA,
    LEDGER_REPAIR_REQUEST_SCHEMA,
    LedgerRepairError,
    PHASE19_VERDICT,
    REPAIR_TYPE_APPEND_ONLY,
    assert_neutral,
    neutral_flags,
)


def repair_request(incident: dict, **overrides) -> dict:
    req = {
        "schema": LEDGER_REPAIR_REQUEST_SCHEMA,
        "request_id": "repair-request-" + incident["incident_id"].lower(),
        "incident_id": incident["incident_id"],
        "repair_type": REPAIR_TYPE_APPEND_ONLY,
        "requested_action": "append_compensating_record",
        "delete_original": False,
        "rewrite_original": False,
        "mark_original_green": False,
        **neutral_flags(),
    }
    req.update(overrides)
    if req.get("delete_original"):
        raise LedgerRepairError("repair_cannot_delete_original")
    if req.get("rewrite_original"):
        raise LedgerRepairError("repair_cannot_rewrite_original")
    if req.get("mark_original_green"):
        raise LedgerRepairError("repair_cannot_mark_original_green")
    assert_neutral(req)
    req["request_hash"] = canonical_hash(req)
    return req


def repair_record(incident: dict, request: dict | None = None, **overrides) -> dict:
    request = request or repair_request(incident)
    if request.get("delete_original"):
        raise LedgerRepairError("repair_cannot_delete_original")
    if request.get("rewrite_original"):
        raise LedgerRepairError("repair_cannot_rewrite_original")
    if request.get("mark_original_green"):
        raise LedgerRepairError("repair_cannot_mark_original_green")
    record = {
        "schema": LEDGER_REPAIR_RECORD_SCHEMA,
        "repair_id": "repair-" + incident["incident_id"].lower(),
        "incident_id": incident["incident_id"],
        "source_phase": incident["source_phase"],
        "source_verdict": incident.get("source_verdict", PHASE19_VERDICT),
        "original_record_hash": incident["original_record_hash"],
        "original_record_preserved": True,
        "repair_type": REPAIR_TYPE_APPEND_ONLY,
        "repair_reason": "Recorded polluted evidence must remain findable but excluded from clean-live claims.",
        "pollution_class": incident["incident_type"],
        "containment_action": "preserve_original_append_repair_exclude_clean_claims",
        "future_gate_treatment": "polluted_evidence_not_clean_live_proof",
        "clean_claim_exclusion": True,
        "operator_review_required": True,
        "may_mark_original_green": False,
        "may_delete_original": False,
        "may_rewrite_original": False,
        **neutral_flags(),
    }
    record.update(overrides)
    assert_neutral(record)
    record["repair_record_hash"] = canonical_hash(record)
    return record
