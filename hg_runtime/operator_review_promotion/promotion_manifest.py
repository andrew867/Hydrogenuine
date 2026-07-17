"""ORP-2 promotion request manifest."""

from __future__ import annotations

from hg_runtime.operator_review_promotion.schemas import assert_neutral, neutral_flags, record_hash


def build_promotion_request_manifest(*, ledger_manifest: dict, eligibility_records: list[dict], requests: list[dict], blocked_records: list[dict]) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "promotion_request_manifest_v1",
        "manifest_id": "orp2-evidence-promotion-request-manifest",
        "source_operator_review_manifest_hash": ledger_manifest["manifest_hash"],
        "eligibility_count": len(eligibility_records),
        "promotion_request_count": len(requests),
        "blocked_promotion_count": len(blocked_records),
        "eligibility_hashes": [r["record_hash"] for r in eligibility_records],
        "promotion_request_hashes": [r["request_hash"] for r in requests],
        "blocked_promotion_hashes": [r["record_hash"] for r in blocked_records],
        "promotion_request_is_promotion": False,
        "eligible_is_truth": False,
        "blocked_is_deletion": False,
        "belief_mutated": False,
        "old_proof_mutated": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
