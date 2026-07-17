"""OES soak iteration and replay records."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.operator_evidence_soak.soak_policy import FIXED_TIME


def build_soak_iteration_result(
    *,
    iteration_id: str,
    iteration_number: int,
    stable_hash: str,
    replay_match: bool,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "soak_iteration_result_v1",
        "iteration_id": iteration_id,
        "iteration_number": iteration_number,
        "stable_hash": stable_hash,
        "replay_match": replay_match,
        "iteration_started_at": FIXED_TIME,
        "iteration_completed_at": FIXED_TIME,
        "doctrine_note": "Replay match is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_soak_replay_result(*, iteration_count: int, stable_hashes: list[str], all_match: bool) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "soak_replay_result_v1",
        "iteration_count": iteration_count,
        "stable_hashes": stable_hashes,
        "all_iterations_match": all_match,
        "deterministic": all_match,
        "doctrine_note": "Determinism is not correctness.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
