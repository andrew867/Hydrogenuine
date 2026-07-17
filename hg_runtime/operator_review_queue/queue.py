"""Operator review queue items."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.operator_review_queue.schemas import (
    QUEUE_ITEM_SCHEMA,
    QUEUE_MANIFEST_SCHEMA,
    QUEUED_FOR_OPERATOR_REVIEW,
    REJECTED_EXTERNAL_SIDE_EFFECT_RISK,
    REJECTED_NOT_SAFE_TO_REVIEW,
    neutral_flags,
)


def queue_item(candidate: dict) -> dict:
    candidate_hash = canonical_hash({"patch_text": candidate["patch_text"], "source": candidate["source"]})
    expected = candidate.get("expected_decision", "")
    if "LIVE_ACTION" in expected:
        status = REJECTED_EXTERNAL_SIDE_EFFECT_RISK
        risk = "live_effect"
    elif "AUTHORITY" in expected or "SECRET" in expected or "ESCAPE" in expected or "NOT_READY" in expected:
        status = REJECTED_NOT_SAFE_TO_REVIEW
        risk = "unsafe"
    else:
        status = QUEUED_FOR_OPERATOR_REVIEW
        risk = "safe" if "SAFE_TO_REVIEW" in expected else "runtime_review"
    item = {
        "schema": QUEUE_ITEM_SCHEMA,
        "queue_item_id": "queue-" + candidate["fixture_id"].lower(),
        "source_patch_candidate_id": candidate["fixture_id"],
        "source_phase38_decision": expected,
        "source_phase40_boundary_decision": "QUEUED_FOR_SEPARATE_APPLY_PHASE",
        "candidate_hash": candidate_hash,
        "candidate_risk_class": risk,
        "operator_review_required": True,
        "queued_status": status,
        "apply_allowed_without_permit": False,
        "patch_text": candidate["patch_text"],
        **neutral_flags(),
    }
    item["queue_item_hash"] = canonical_hash(item)
    return item


def queue_manifest(items: list[dict]) -> dict:
    manifest = {
        "schema": QUEUE_MANIFEST_SCHEMA,
        "queue_manifest_id": "phase41-review-queue-manifest",
        "queue_item_count": len(items),
        "queue_item_hashes": [item["queue_item_hash"] for item in items],
        "queue_entry_is_approval": False,
        **neutral_flags(),
    }
    manifest["queue_manifest_hash"] = canonical_hash(manifest)
    return manifest
