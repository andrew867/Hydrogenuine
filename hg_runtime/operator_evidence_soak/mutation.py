"""OES mutation probe and result records."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import MUTATION_PROBE_TYPES, assert_neutral, neutral_flags, record_hash
from hg_runtime.operator_evidence_soak.soak_policy import FIXED_TIME


def build_soak_mutation_probe(*, probe_id: str, probe_type: str, target_ref: str) -> dict:
    if probe_type not in MUTATION_PROBE_TYPES:
        raise ValueError(f"invalid_probe_type:{probe_type}")
    record = {
        "schema_version": "1",
        "record_type": "soak_mutation_probe_v1",
        "probe_id": probe_id,
        "probe_type": probe_type,
        "target_ref": target_ref,
        "created_at": FIXED_TIME,
        "doctrine_note": "Mutation detection is not repair.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_soak_mutation_result(
    *,
    result_id: str,
    probe_id: str,
    mismatch_detected: bool,
    original_preserved: bool = True,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "soak_mutation_result_v1",
        "result_id": result_id,
        "probe_id": probe_id,
        "mismatch_detected": mismatch_detected,
        "original_preserved": original_preserved,
        "mutation_auto_repaired": False,
        "deletion_performed": False,
        "patch_request_applied": False,
        "doctrine_note": "Mutation detection is not repair.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
