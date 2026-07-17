"""LEB-3 provisional belief revision from local evidence links."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.bridge_replay import replay_wmbr_bridge
from hg_runtime.local_evidence_bridge.claim_linker import build_claim_bridge
from hg_runtime.local_evidence_bridge.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash
from hg_runtime.local_evidence_bridge.text_ingestion import ingest_text_source
from hg_runtime.local_evidence_bridge.verification_task_linker import build_verification_task_links
from hg_runtime.local_evidence_bridge.wmbr_bridge_manifest import build_wmbr_bridge_manifest

PATHS = ["tests/fixtures/local_evidence/source_001.md", "tests/fixtures/local_evidence/source_002.txt"]


def _belief_state(*, claim_id: str, status: str, link_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "local_evidence_belief_state_v1",
        "belief_state_id": f"local-belief-{claim_id}",
        "claim_id": claim_id,
        "source_link_id": link_id,
        "belief_status": status,
        "belief_state_is_truth": False,
        "claim_marked_true": False,
        "certainty_claimed": False,
        "local_evidence_only": True,
        "original_wmbr_records_preserved": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def _revision(*, state: dict, from_status: str, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "local_evidence_belief_revision_v1",
        "revision_id": f"local-revision-{state['claim_id']}",
        "claim_id": state["claim_id"],
        "from_status": from_status,
        "to_status": state["belief_status"],
        "source_link_id": state["source_link_id"],
        "revision_reason": reason,
        "belief_revision_is_certainty": False,
        "truth_claimed": False,
        "certainty_claimed": False,
        "old_wmbr_proof_bundle_mutated": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def _contradiction(*, claim_id: str, link_id: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "local_evidence_contradiction_v1",
        "contradiction_id": f"local-contradiction-{claim_id}",
        "claim_id": claim_id,
        "source_link_id": link_id,
        "truth_resolved": False,
        "contradiction_is_truth_resolution": False,
        "review_required": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def _provenance_chain(*, state: dict, link: dict) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "local_evidence_provenance_chain_v1",
        "provenance_chain_id": f"local-provenance-{state['claim_id']}",
        "claim_id": state["claim_id"],
        "belief_state_id": state["belief_state_id"],
        "source_link_id": link["link_id"],
        "evidence_receipt_id": link["evidence_receipt_id"],
        "evidence_receipt_hash": link["evidence_receipt_hash"],
        "provenance_chain_is_not_truth": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_local_revision_run(root) -> dict:
    rows = [ingest_text_source(root, path, source_id=f"src-{i}") for i, path in enumerate(PATHS, start=1)]
    receipts = [row["evidence_receipt"] for row in rows]
    bridge = build_claim_bridge(receipts)
    task_links = build_verification_task_links(bridge["links"])
    bridge_manifest = build_wmbr_bridge_manifest(
        links=bridge["links"],
        supports=bridge["supports"],
        contradictions=bridge["contradictions"],
        task_links=task_links,
    )
    bridge_replay = replay_wmbr_bridge(bridge["links"], bridge["supports"], bridge["contradictions"], task_links, bridge_manifest)
    states: list[dict] = []
    revisions: list[dict] = []
    contradictions: list[dict] = []
    provenance: list[dict] = []
    for link in bridge["links"]:
        if link["link_kind"] == "SUPPORT_CANDIDATE":
            status = "PROVISIONALLY_SUPPORTED"
            reason = "LOCAL_EVIDENCE_SUPPORT_CANDIDATE"
        else:
            status = "CONTRADICTED"
            reason = "LOCAL_EVIDENCE_CONTRADICTION_CANDIDATE"
        state = _belief_state(claim_id=link["claim_id"], status=status, link_id=link["link_id"])
        states.append(state)
        revisions.append(_revision(state=state, from_status="UNVERIFIED", reason=reason))
        provenance.append(_provenance_chain(state=state, link=link))
        if status == "CONTRADICTED":
            contradictions.append(_contradiction(claim_id=link["claim_id"], link_id=link["link_id"]))
    insufficient = _belief_state(
        claim_id="wmbr-fixture-claim-local-evidence-insufficient",
        status="INSUFFICIENT_EVIDENCE",
        link_id="UNKNOWN",
    )
    states.append(insufficient)
    revisions.append(_revision(state=insufficient, from_status="UNVERIFIED", reason="NO_LOCAL_EVIDENCE_LINK"))
    return {
        "bridge": {
            "receipts": receipts,
            "links": bridge["links"],
            "supports": bridge["supports"],
            "contradictions": bridge["contradictions"],
            "task_links": task_links,
            "manifest": bridge_manifest,
            "replay": bridge_replay,
        },
        "belief_states": states,
        "belief_revisions": revisions,
        "local_contradictions": contradictions,
        "provenance_chains": provenance,
    }


def build_local_revision_manifest(run: dict) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "local_revision_manifest_v1",
        "manifest_id": "leb3-local-evidence-belief-revision",
        "belief_state_count": len(run["belief_states"]),
        "belief_revision_count": len(run["belief_revisions"]),
        "contradiction_count": len(run["local_contradictions"]),
        "provenance_chain_count": len(run["provenance_chains"]),
        "belief_state_hashes": [r["record_hash"] for r in run["belief_states"]],
        "belief_revision_hashes": [r["record_hash"] for r in run["belief_revisions"]],
        "contradiction_hashes": [r["record_hash"] for r in run["local_contradictions"]],
        "provenance_chain_hashes": [r["record_hash"] for r in run["provenance_chains"]],
        "local_evidence_can_only_provisionally_support": True,
        "belief_state_is_not_truth": True,
        "belief_revision_is_not_certainty": True,
        "original_wmbr_records_preserved": True,
        "old_wmbr_proof_bundles_mutated": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
