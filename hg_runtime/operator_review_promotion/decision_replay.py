"""Replay helpers for ORP-1 decision ledgers."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import OperatorReviewPromotionError, assert_neutral, neutral_flags, record_hash


def replay_decision_ledger(decisions: list[dict], links: list[dict], rejections: list[dict], deferrals: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [d.get("decision_hash") for d in decisions] != manifest.get("decision_hashes", []):
        failures.append("decision_hash_mismatch")
    if [l.get("record_hash") for l in links] != manifest.get("reviewed_link_hashes", []):
        failures.append("reviewed_link_hash_mismatch")
    for record in [*decisions, *links, *rejections, *deferrals]:
        expected = record_hash(record)
        stored = record.get("record_hash") or record.get("decision_hash")
        if stored != expected:
            failures.append(f"record_hash_mismatch:{record.get('decision_id') or record.get('link_id')}")
    try:
        for record in [*decisions, *links, *rejections, *deferrals, manifest]:
            assert_neutral(record)
    except OperatorReviewPromotionError as exc:
        failures.append(f"boundary_violation:{exc}")
    replay = {
        "schema_version": "1",
        "record_type": "operator_review_replay_record_v1",
        "replay_id": "orp1-operator-review-decision-ledger-replay",
        "replay_preserves_ledger_hashes": not failures,
        "receipt_chain_root": record_hash({"records": [record_hash(r) for r in [*decisions, *links, *rejections, *deferrals, manifest]]}),
        "failures": failures,
        "operator_review_treated_as_truth": False,
        "belief_promotion_automatic": False,
        **neutral_flags(),
    }
    replay["record_hash"] = record_hash(replay)
    return replay
