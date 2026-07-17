"""DTX soak schema builders."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import assert_neutral, neutral_flags, record_hash


def build_dtx_soak_iteration(
    *,
    iteration_id: str,
    iteration_number: int,
    stable_hash: str,
    replay_match: bool,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_soak_iteration_v1",
        "iteration_id": iteration_id,
        "iteration_number": iteration_number,
        "stable_hash": stable_hash,
        "replay_match": replay_match,
        "soak_treated_as_truth": False,
        "replay_match_treated_as_truth": False,
        "determinism_treated_as_correctness": False,
        "doctrine_note": "Soak is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_dtx_soak_manifest(*, manifest_id: str, dtx_manifest_ref: str, iteration_count: int) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "dtx_soak_manifest_v1",
        "manifest_id": manifest_id,
        "dtx_manifest_ref": dtx_manifest_ref,
        "iteration_count": iteration_count,
        "explicit_manifest_only": True,
        **neutral_flags(),
    }
    record["manifest_hash"] = record_hash(record)
    assert_neutral(record)
    return record
