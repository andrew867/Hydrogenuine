"""SQP redaction, quarantine, and review hint schema records."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_redaction_status(*, source_id: str, status: str = "COMPLETE") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_redaction_status_v1",
        "source_id": source_id,
        "status": status,
        "redaction_audit_ref": "docs/proofs/autonomous_agent_zero/REVIEWED-LOCAL-EVIDENCE-BETA/20260620T180648Z/redaction_audit.json",
        "checked_at": FIXED_TIME,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_quarantine_history(*, source_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_quarantine_history_v1",
        "source_id": source_id,
        "quarantine_event_refs": [],
        "latest_status": "NONE",
        "adapted_at": FIXED_TIME,
        "adapter_mode": "read_only",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_review_policy_hint(*, source_id: str, hint: str = "SUGGEST_REVIEW") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_review_policy_hint_v1",
        "source_id": source_id,
        "hint": hint,
        "hint_rationale": ["schema foundation fixture; review hint is advisory only"],
        "priority": 2,
        "emitted_at": FIXED_TIME,
        "doctrine_note": "Review policy hints are not operator approval.",
        "review_hint_treated_as_operator_approval": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
