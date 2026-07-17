"""OES soak replay helpers."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import assert_neutral, neutral_flags, record_hash


def build_soak_replay_record(*, expected_hash: str, observed_hash: str, match: bool) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "soak_replay_result_v1",
        "expected_stable_hash": expected_hash,
        "observed_stable_hash": observed_hash,
        "replay_match": match,
        "replay_match_is_truth": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
