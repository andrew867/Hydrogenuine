"""Phase 40 incident fixtures."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.ledger_repair.schemas import (
    LEDGER_INCIDENT_RECORD_SCHEMA,
    PHASE19_INCIDENT_ID,
    PHASE19_VERDICT,
    REPAIR_TYPE_APPEND_ONLY,
    neutral_flags,
)


def incident_record(**overrides) -> dict:
    record = {
        "schema": LEDGER_INCIDENT_RECORD_SCHEMA,
        "incident_id": PHASE19_INCIDENT_ID,
        "incident_type": "DEBUG_UNAUTHORIZED_OR_OUT_OF_ENVELOPE",
        "source_phase": 19,
        "source_verdict": PHASE19_VERDICT,
        "must_preserve_original": True,
        "may_rewrite_original": False,
        "may_delete_original": False,
        "may_mark_original_green": False,
        "clean_live_claim_allowed": False,
        "repair_allowed": REPAIR_TYPE_APPEND_ONLY,
        "original_record_hash": "sha256:phase19-debug-dispatch-incident-preserved",
        **neutral_flags(),
    }
    record.update(overrides)
    record["incident_hash"] = canonical_hash(record)
    return record


def clean_incident_fixture() -> dict:
    return incident_record(
        incident_id="CLEAN_INCIDENT_FIXTURE",
        incident_type="NO_POLLUTION",
        source_phase=40,
        source_verdict="GREEN_FIXTURE_ONLY",
        clean_live_claim_allowed=True,
        original_record_hash="sha256:clean-fixture",
    )


def phase19_incident_findable(records: list[dict]) -> bool:
    return any(row.get("incident_id") == PHASE19_INCIDENT_ID for row in records)

