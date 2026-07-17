"""LEB-2 bridge manifest."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash


def build_wmbr_bridge_manifest(
    *,
    links: list[dict],
    supports: list[dict],
    contradictions: list[dict],
    task_links: list[dict],
) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "wmbr_bridge_manifest_v1",
        "manifest_id": "leb2-evidence-wmbr-linker",
        "evidence_claim_link_count": len(links),
        "support_record_count": len(supports),
        "contradiction_record_count": len(contradictions),
        "verification_task_link_count": len(task_links),
        "link_hashes": [r["record_hash"] for r in links],
        "support_hashes": [r["record_hash"] for r in supports],
        "contradiction_hashes": [r["record_hash"] for r in contradictions],
        "task_link_hashes": [r["record_hash"] for r in task_links],
        "support_link_is_not_proof": True,
        "contradiction_link_is_not_truth_resolution": True,
        "evidence_receipt_is_not_automatic_belief_revision": True,
        "bridge_does_not_mutate_wmbr03_ledger": True,
        "wmbr03_ledger_mutated": False,
        "reviewable_input_only": True,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
