"""ORP-3 promotion gate replay."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import OperatorReviewPromotionError, assert_neutral, neutral_flags, record_hash


def replay_promotion_gate(gate_results: list[dict], revision_inputs: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [r["gate_hash"] for r in gate_results] != manifest.get("promotion_gate_hashes", []):
        failures.append("gate_hash_mismatch")
    if [r["record_hash"] for r in revision_inputs] != manifest.get("revision_input_hashes", []):
        failures.append("revision_input_hash_mismatch")
    for record in [*gate_results, *revision_inputs]:
        stored = record.get("gate_hash") or record.get("record_hash")
        if stored != record_hash(record):
            failures.append("record_hash_mismatch")
    try:
        for record in [*gate_results, *revision_inputs, manifest]:
            assert_neutral(record)
    except OperatorReviewPromotionError as exc:
        failures.append(f"boundary_violation:{exc}")
    replay = {
        "schema_version": "1",
        "record_type": "operator_review_replay_record_v1",
        "replay_id": "orp3-promotion-gate-replay",
        "replay_preserves_gate_hashes": not failures,
        "receipt_chain_root": record_hash({"records": [record_hash(r) for r in [*gate_results, *revision_inputs, manifest]]}),
        "failures": failures,
        **neutral_flags(),
    }
    replay["record_hash"] = record_hash(replay)
    return replay
