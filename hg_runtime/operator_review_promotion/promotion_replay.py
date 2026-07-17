"""ORP-2 promotion request replay."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import OperatorReviewPromotionError, assert_neutral, neutral_flags, record_hash


def replay_promotion_requests(eligibility_records: list[dict], requests: list[dict], blocked_records: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [r["record_hash"] for r in eligibility_records] != manifest.get("eligibility_hashes", []):
        failures.append("eligibility_hash_mismatch")
    if [r["request_hash"] for r in requests] != manifest.get("promotion_request_hashes", []):
        failures.append("request_hash_mismatch")
    if [r["record_hash"] for r in blocked_records] != manifest.get("blocked_promotion_hashes", []):
        failures.append("blocked_hash_mismatch")
    for record in [*eligibility_records, *requests, *blocked_records]:
        stored = record.get("record_hash") or record.get("request_hash")
        if stored != record_hash(record):
            failures.append("record_hash_mismatch")
    try:
        for record in [*eligibility_records, *requests, *blocked_records, manifest]:
            assert_neutral(record)
    except OperatorReviewPromotionError as exc:
        failures.append(f"boundary_violation:{exc}")
    replay = {
        "schema_version": "1",
        "record_type": "operator_review_replay_record_v1",
        "replay_id": "orp2-evidence-promotion-request-replay",
        "replay_preserves_promotion_hashes": not failures,
        "receipt_chain_root": record_hash({"records": [record_hash(r) for r in [*eligibility_records, *requests, *blocked_records, manifest]]}),
        "failures": failures,
        **neutral_flags(),
    }
    replay["record_hash"] = record_hash(replay)
    return replay
