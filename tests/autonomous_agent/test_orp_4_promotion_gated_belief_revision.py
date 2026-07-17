"""ORP-4 promotion-gated local belief revision tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.promotion_gated_belief_revision import (
    build_promotion_gated_belief_revision,
    validate_orp4_gate,
)
from hg_runtime.operator_review_promotion.redaction import secret_scan
from hg_runtime.operator_review_promotion.reviewed_revision_replay import replay_reviewed_revision
from hg_runtime.operator_review_promotion.schemas import PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_promotion_gated_belief_revision(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_ORP_4_PROMOTION_GATED_BELIEF_REVISION",
        "orp3_green": True,
        "reviewed_local_belief_states_written": True,
        "reviewed_local_belief_revisions_written": True,
        "reviewed_local_contradictions_written": True,
        "reviewed_local_provenance_chains_written": True,
        "reviewed_revision_manifest_written": True,
        "reviewed_belief_still_provisional": True,
        "operator_reviewed_not_truth": True,
        "support_remains_provisional_only": True,
        "contradiction_unresolved": True,
        "rejected_evidence_excluded_but_preserved": True,
        "old_records_preserved": True,
        "no_truth_or_certainty": True,
        "no_authority": True,
        "no_tools": True,
        "no_live_effects": True,
        "replay_preserves_reviewed_revision_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_orp4_writes_reviewed_belief_states():
    assert _layer()["run"]["reviewed_belief_states"]


def test_orp4_writes_reviewed_belief_revisions():
    assert _layer()["run"]["reviewed_belief_revisions"]


def test_orp4_writes_contradictions_and_provenance():
    run = _layer()["run"]
    assert run["reviewed_local_contradictions"]
    assert run["reviewed_local_provenance_chains"]


def test_orp4_manifest_written():
    assert _layer()["manifest"]["record_type"] == "reviewed_revision_manifest_v1"


def test_orp4_reviewed_belief_still_provisional():
    states = _layer()["run"]["reviewed_belief_states"]
    assert all(state["reviewed_belief_is_still_provisional"] for state in states)
    assert all(state["belief_status"] == "PROVISIONALLY_SUPPORTED" for state in states)


def test_orp4_operator_reviewed_does_not_mean_true():
    states = _layer()["run"]["reviewed_belief_states"]
    assert all(not state["operator_reviewed_means_true"] for state in states)
    assert all(not state["truth_claimed"] for state in states)


def test_orp4_support_remains_provisionally_supported_only():
    states = _layer()["run"]["reviewed_belief_states"]
    assert {state["support_level"] for state in states} == {"PROVISIONALLY_SUPPORTED"}


def test_orp4_contradiction_remains_unresolved():
    contradictions = _layer()["run"]["reviewed_local_contradictions"]
    assert all(not row["truth_resolved"] for row in contradictions)


def test_orp4_rejected_evidence_excluded_but_preserved():
    manifest = _layer()["manifest"]
    assert manifest["rejected_evidence_excluded_but_preserved"] is True


def test_orp4_old_records_preserved():
    manifest = _layer()["manifest"]
    assert manifest["old_records_preserved"] is True
    assert manifest["old_wmbr_proof_bundles_mutated"] is False
    assert manifest["old_leb_proof_bundles_mutated"] is False


def test_orp4_no_truth_certainty_authority_tools_live_effects():
    layer = _layer()
    run = layer["run"]
    records = (
        run["reviewed_belief_states"]
        + run["reviewed_belief_revisions"]
        + run["reviewed_local_contradictions"]
        + run["reviewed_local_provenance_chains"]
        + [layer["manifest"]]
    )
    assert all(not row["truth_claimed"] for row in records)
    assert all(not row["authority_granted"] for row in records)
    assert all(not row["tools_authorized"] for row in records)
    assert all(not row["live_external_side_effects_created"] for row in records)


def test_orp4_replay_preserves_reviewed_revision_hashes():
    assert _layer()["replay"]["replay_preserves_reviewed_revision_hashes"] is True


def test_orp4_replay_rejects_mutated_state():
    layer = _layer()
    run = {**layer["run"], "reviewed_belief_states": [dict(row) for row in layer["run"]["reviewed_belief_states"]]}
    run["reviewed_belief_states"][0]["belief_status"] = "VERIFIED_TRUE"
    replay = replay_reviewed_revision(run, layer["manifest"])
    assert replay["replay_preserves_reviewed_revision_hashes"] is False


def test_orp4_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_orp4_preserves_phase19_yellow_and_phase24_infrastructure_only():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


def test_orp4_gate_passes_full_summary():
    assert validate_orp4_gate(_summary())["ok"] is True


def test_orp4_gate_refuses_truth_or_certainty():
    assert validate_orp4_gate(_summary(no_truth_or_certainty=False))["ok"] is False
    assert validate_orp4_gate(_summary(truth_claimed=True))["ok"] is False


def test_orp4_gate_refuses_missing_reviewed_states():
    assert validate_orp4_gate(_summary(reviewed_local_belief_states_written=False))["ok"] is False


def test_orp4_gate_refuses_automatic_promotion():
    assert validate_orp4_gate(_summary(belief_promotion_automatic=True))["ok"] is False


def test_orp4_gate_refuses_authority_or_tools():
    assert validate_orp4_gate(_summary(authority_granted=True))["ok"] is False
    assert validate_orp4_gate(_summary(tools_authorized=True))["ok"] is False


def test_orp4_gate_refuses_without_replay():
    assert validate_orp4_gate(_summary(replay_preserves_reviewed_revision_hashes=False))["ok"] is False
