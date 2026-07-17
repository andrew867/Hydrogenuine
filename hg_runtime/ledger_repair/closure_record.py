"""Incident closure records."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.ledger_repair.schemas import CLOSURE_BOUNDED, INCIDENT_CLOSURE_RECORD_SCHEMA, neutral_flags


def closure_record(incident: dict, repair: dict, *, original_findable: bool = True) -> dict:
    record = {
        "schema": INCIDENT_CLOSURE_RECORD_SCHEMA,
        "closure_id": "closure-" + incident["incident_id"].lower(),
        "incident_id": incident["incident_id"],
        "repair_id": repair["repair_id"],
        "closure_status": CLOSURE_BOUNDED,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "polluted_evidence_excluded_from_clean_claims": True,
        "original_incident_still_findable": original_findable,
        "operator_ack_required_for_future_clean_live_claim": True,
        **neutral_flags(),
    }
    record["closure_hash"] = canonical_hash(record)
    return record

