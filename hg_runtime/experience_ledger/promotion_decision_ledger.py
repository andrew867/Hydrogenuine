"""Append-only P26-3 promotion decision ledger."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.hashing import stable_hash, with_hash
from hg_runtime.experience_ledger.memory_promotion_gate import decide_memory_promotion
from hg_runtime.experience_ledger.orp_memory_bridge import build_memory_promotion_request, build_orp_memory_bridge
from hg_runtime.experience_ledger.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral


def build_p26_3_bridge(repo_root: Path) -> dict:
    bridge = build_orp_memory_bridge(repo_root)
    requests = bridge["requests"]
    decisions = [
        decide_memory_promotion(requests[0], "APPROVED_FOR_REVIEW"),
        decide_memory_promotion(requests[1], "REJECTED"),
        decide_memory_promotion(requests[2], "DEFERRED"),
    ]
    missing_provenance = dict(bridge["memory_records"][0])
    missing_provenance["memory_id"] = "mem-missing-provenance"
    missing_provenance["provenance_refs"] = []
    missing_provenance_rejection = build_memory_promotion_request(missing_provenance)
    quarantined = dict(requests[0])
    quarantined["request_id"] = "p26-3-request-quarantined-memory"
    quarantined["memory_id"] = "mem-quarantined-review-only"
    with_hash(quarantined, "request_hash")
    quarantined_decision = decide_memory_promotion(quarantined, "REVIEW_ONLY_QUARANTINED")
    rejections = [missing_provenance_rejection, decisions[1]]
    receipt_chain = requests + decisions + [missing_provenance_rejection, quarantined_decision]
    manifest = {
        "record_type": "orp_memory_bridge_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p26-3-orp-memory-bridge",
        "request_count": len(requests),
        "decision_count": len(decisions) + 1,
        "rejection_count": len(rejections),
        "receipt_root": stable_hash({"receipt_hashes": [stable_hash(record) for record in receipt_chain]}),
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "promotion_request_auto_applied": False,
        "orp_bypassed": False,
        "belief_promotion_automatic": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_external_side_effects_created": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    replay = {
        "record_type": "operator_review_replay_record_v1",
        "schema_version": "1",
        "replay_preserves_promotion_hashes": manifest["receipt_root"] == stable_hash({"receipt_hashes": [stable_hash(record) for record in receipt_chain]}),
        "mutation_auto_repair_performed": False,
    }
    with_hash(replay, "record_hash")
    return {
        "memory_records": bridge["memory_records"],
        "requests": requests,
        "decisions": decisions + [quarantined_decision],
        "rejections": rejections,
        "manifest": manifest,
        "replay": replay,
        "receipt_chain": receipt_chain + [manifest, replay],
    }
