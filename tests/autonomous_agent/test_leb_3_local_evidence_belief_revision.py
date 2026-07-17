"""LEB-3 provisional local-evidence belief revision tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.local_belief_revision import build_local_revision_manifest, build_local_revision_run
from hg_runtime.local_evidence_bridge.local_revision_replay import replay_local_revision
from hg_runtime.local_evidence_bridge.schemas import PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    run = build_local_revision_run(ROOT)
    manifest = build_local_revision_manifest(run)
    replay = replay_local_revision(run, manifest)
    return run, manifest, replay


def test_leb3_creates_local_evidence_belief_states():
    run, _, _ = _layer()
    assert run["belief_states"]


def test_leb3_local_evidence_supports_only_provisionally():
    run, manifest, _ = _layer()
    statuses = {state["belief_status"] for state in run["belief_states"]}
    assert "PROVISIONALLY_SUPPORTED" in statuses
    assert "VERIFIED_TRUE" not in statuses
    assert manifest["local_evidence_can_only_provisionally_support"] is True


def test_leb3_contradictory_local_evidence_creates_contradiction():
    run, _, _ = _layer()
    assert run["local_contradictions"]
    assert all(not row["truth_resolved"] for row in run["local_contradictions"])


def test_leb3_insufficient_local_evidence_remains_insufficient():
    run, _, _ = _layer()
    assert any(state["belief_status"] == "INSUFFICIENT_EVIDENCE" for state in run["belief_states"])


def test_leb3_belief_state_is_not_truth():
    run, manifest, _ = _layer()
    assert all(not state["belief_state_is_truth"] for state in run["belief_states"])
    assert all(not state["truth_claimed"] for state in run["belief_states"])
    assert manifest["belief_state_is_not_truth"] is True


def test_leb3_belief_revision_is_not_certainty():
    run, manifest, _ = _layer()
    assert all(not revision["belief_revision_is_certainty"] for revision in run["belief_revisions"])
    assert all(not revision["certainty_claimed"] for revision in run["belief_revisions"])
    assert manifest["belief_revision_is_not_certainty"] is True


def test_leb3_original_wmbr_records_preserved():
    run, manifest, _ = _layer()
    assert all(state["original_wmbr_records_preserved"] for state in run["belief_states"])
    assert manifest["original_wmbr_records_preserved"] is True
    assert manifest["old_wmbr_proof_bundles_mutated"] is False


def test_leb3_no_authority_tools_or_live_effects():
    run, manifest, _ = _layer()
    rows = run["belief_states"] + run["belief_revisions"] + run["local_contradictions"] + run["provenance_chains"] + [manifest]
    assert all(not row["authority_granted"] for row in rows)
    assert all(not row["tools_authorized"] for row in rows)
    assert all(not row["live_external_side_effects_created"] for row in rows)


def test_leb3_replay_preserves_local_revision_hashes():
    *_, replay = _layer()
    assert replay["replay_preserves_local_revision_hashes"] is True


def test_leb3_replay_rejects_mutated_revision():
    run, manifest, _ = _layer()
    mutated = {**run, "belief_revisions": [dict(row) for row in run["belief_revisions"]]}
    mutated["belief_revisions"][0]["record_hash"] = "mutated"
    replay = replay_local_revision(mutated, manifest)
    assert replay["replay_preserves_local_revision_hashes"] is False


def test_leb3_preserves_phase19_yellow_and_phase24_infrastructure_only():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"
