"""SLE-RC artifact index builders."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.schemas import (
    COMPONENT_FAMILIES,
    PROVIDER_MODE,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_rc_artifact_index(*, index_id: str, entries: list[dict]) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_artifact_index_v1",
        "index_id": index_id,
        "provider_mode": PROVIDER_MODE,
        "component_families": list(COMPONENT_FAMILIES),
        "entry_count": len(entries),
        "entries": entries,
        "doctrine_note": "Artifact index is not authority.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_rc_release_risk_record(*, risk_id: str, risk_key: str, severity: str, detail: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_release_risk_record_v1",
        "risk_id": risk_id,
        "risk_key": risk_key,
        "severity": severity,
        "detail": detail,
        "release_candidate_is_deployment": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
