"""SLE-RC soak replay helpers."""

from __future__ import annotations

from typing import Any

from hg_runtime.safe_local_evidence_rc.schemas import assert_neutral, neutral_flags, record_hash


def rc_stable_hash(payload: Any) -> str:
    return record_hash(payload)


def build_rc_soak_iteration(*, iteration_id: str, iteration_number: int, stable_hash: str, replay_match: bool) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_soak_iteration_v1",
        "iteration_id": iteration_id,
        "iteration_number": iteration_number,
        "stable_hash": stable_hash,
        "replay_match": replay_match,
        "soak_treated_as_truth": False,
        "replay_match_treated_as_truth": False,
        "mutation_detection_is_repair": False,
        "mutation_auto_repaired": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_rc_soak_manifest(*, manifest_id: str, iteration_count: int, oec_manifest_ref: str, dtx_manifest_ref: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_soak_manifest_v1",
        "manifest_id": manifest_id,
        "iteration_count": iteration_count,
        "oec_manifest_ref": oec_manifest_ref,
        "dtx_manifest_ref": dtx_manifest_ref,
        "explicit_manifest_only": True,
        "soak_treated_as_truth": False,
        "stable_hash_treated_as_correctness": False,
        **neutral_flags(),
    }
    record["manifest_hash"] = record_hash(record)
    assert_neutral(record)
    return record
