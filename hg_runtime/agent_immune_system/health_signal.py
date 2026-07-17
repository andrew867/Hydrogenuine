"""AIS health_signal_v1 builder."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.schemas import assert_neutral, neutral_flags
from hg_runtime.agent_immune_system.severity import validate_severity


def build_health_signal(
    *,
    signal_id: str,
    source_component: str,
    signal_type: str,
    severity: str,
    weight: float = 1.0,
    evidence_ref: str,
    phase_ref: str | None = None,
) -> dict:
    validate_severity(severity)
    record = {
        "schema_version": "1",
        "record_type": "health_signal_v1",
        "signal_id": signal_id,
        "source_component": source_component,
        "signal_type": signal_type,
        "severity": severity,
        "weight": weight,
        "evidence_ref": evidence_ref,
        "phase_ref": phase_ref,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
