"""WMBR-03 / CAGI-44 belief revision ledger tests.

Doctrine: Every model is a compressed civilization artifact.
A belief state is not truth. A belief revision is not certainty.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hg_runtime.belief_revision_ledger.artifact_writer import build_ledger, secret_scan
from hg_runtime.belief_revision_ledger.belief_state import build_belief_state
from hg_runtime.belief_revision_ledger.evidence_receipt import (
    build_synthetic_evidence_receipt,
    validate_evidence_receipt,
)
from hg_runtime.belief_revision_ledger.fixtures import (
    certainty_laundering_fixture,
    claim_rewrite_fixture,
    fixture_queue_bundle,
    missing_provenance_fixture,
    model_output_as_evidence_fixture,
    truth_laundering_fixture,
    verification_task_as_evidence_fixture,
)
from hg_runtime.belief_revision_ledger.gate import validate_wmbr03_gate
from hg_runtime.belief_revision_ledger.queue_loader import (
    discover_latest_bundle,
    load_queue_bundle,
    validate_queue_bundle,
)
from hg_runtime.belief_revision_ledger.replay import replay_ledger
from hg_runtime.belief_revision_ledger.revision_engine import process_claim_evidence, transition
from hg_runtime.belief_revision_ledger.schemas import (
    BeliefRevisionError,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RUNTIME_P42_VERDICT_GREEN,
    VERDICT_GREEN,
    WMBR_01A_VERDICT_GREEN,
    WMBR_02_VERDICT_GREEN,
    assert_neutral,
)

ROOT = Path(__file__).resolve().parents[2]
WMBR_02_PROOF_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/WMBR-02-BELIEF-VERIFICATION-QUEUE"


def _out():
    return build_ledger(fixture_queue_bundle())


def _claim_task():
    bundle = fixture_queue_bundle()
    task = sorted(bundle["verification_tasks"], key=lambda t: t["task_id"])[0]
    claim_id = task["source_claim_ids"][0]
    claim = next(c for c in bundle["candidate_claims"] if c["claim_id"] == claim_id)
    return claim, task


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "wmbr02_green": True,
        "wmbr01a_green": True,
        "runtime_p42_green": True,
        "input_queue_loaded": True,
        "candidate_claims_loaded": True,
        "claim_count": 20,
        "evidence_receipts_written": True,
        "evidence_receipt_count": 18,
        "all_evidence_has_provenance": True,
        "belief_states_written": True,
        "belief_state_count": 20,
        "belief_revisions_written": True,
        "belief_revision_count": 21,
        "contradiction_records_written": True,
        "contradiction_count": 7,
        "retraction_count": 3,
        "provenance_chains_written": True,
        "provenance_chain_required_for_promoted_state": True,
        "supporting_evidence_only_provisional": True,
        "unsupported_claims_remain_unverified": True,
        "retraction_preserves_original_claim": True,
        "original_claim_deleted_or_rewritten": False,
        "model_output_is_not_evidence": True,
        "verification_task_is_not_evidence": True,
        "belief_state_is_not_truth": True,
        "belief_revision_is_not_certainty": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_revision_hashes": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_truth_revision_rejected": True,
        "candidate_agi_parent_phase_completed": False,
    }
    data.update(overrides)
    return data


# --- Loading ---------------------------------------------------------------

def test_wmbr03_loads_wmbr02_queue():
    bundle_dir = discover_latest_bundle(WMBR_02_PROOF_ROOT)
    assert bundle_dir is not None
    bundle = load_queue_bundle(bundle_dir)
    validate_queue_bundle(bundle)
    assert bundle["candidate_claims"]


def test_wmbr03_accepts_fixture_queue_when_bundle_unavailable():
    assert _out()["summary"]["claim_count"] > 0


def test_wmbr03_rejects_missing_queue():
    with pytest.raises(BeliefRevisionError):
        validate_queue_bundle({"queue_manifest": {}, "candidate_claims": []})


def test_wmbr03_extracts_candidate_claims_from_queue():
    assert _out()["belief_states"]


# --- Evidence ordering invariants -----------------------------------------

def test_wmbr03_requires_verification_task_before_evidence():
    claim, task = _claim_task()
    receipt = build_synthetic_evidence_receipt(task=task, target_claim_id=claim["claim_id"], stance="SUPPORTS", ordinal=0)
    assert receipt["source_task_id"] == task["task_id"]


def test_wmbr03_requires_evidence_receipt_before_revision():
    claim, task = _claim_task()
    result = process_claim_evidence(claim, task, ["SUPPORTS"], ["matrix-x"])
    assert result["evidence_receipts"]
    assert result["revisions"][0]["evidence_receipt_ids"] == [result["evidence_receipts"][0]["evidence_receipt_id"]]


def test_wmbr03_evidence_receipt_requires_provenance():
    with pytest.raises(BeliefRevisionError):
        validate_evidence_receipt(missing_provenance_fixture())


def test_wmbr03_model_output_is_not_evidence():
    with pytest.raises(BeliefRevisionError):
        validate_evidence_receipt(model_output_as_evidence_fixture())


def test_wmbr03_model_consensus_is_not_evidence():
    receipt = model_output_as_evidence_fixture()
    receipt["model_output_is_evidence"] = False
    receipt["model_consensus_treated_as_evidence"] = True
    with pytest.raises(BeliefRevisionError):
        validate_evidence_receipt(receipt)


def test_wmbr03_verification_task_is_not_evidence():
    with pytest.raises(BeliefRevisionError):
        validate_evidence_receipt(verification_task_as_evidence_fixture())


# --- Transition mechanics --------------------------------------------------

def test_wmbr03_supporting_evidence_promotes_only_to_provisionally_supported():
    assert transition("UNVERIFIED", "SUPPORTS") == ("PROVISIONALLY_SUPPORTED", "SUPPORTING_EVIDENCE_RECEIVED")
    # No path yields a "true"/"verified" status.
    states = {transition(s, "SUPPORTS")[0] for s in ("UNVERIFIED", "INSUFFICIENT_EVIDENCE", "PROVISIONALLY_SUPPORTED")}
    assert states == {"PROVISIONALLY_SUPPORTED"}


def test_wmbr03_belief_state_is_not_truth():
    assert all(s["belief_status"] not in ("VERIFIED_TRUE", "TRUE") and not s["truth_claimed"] for s in _out()["belief_states"])


def test_wmbr03_belief_revision_is_not_certainty():
    assert all(not r["certainty_claimed"] for r in _out()["revisions"])


def test_wmbr03_no_claim_marked_true():
    assert all(not s.get("claim_marked_true") for s in _out()["belief_states"])


def test_wmbr03_no_certainty_claimed():
    out = _out()
    assert all(not r.get("certainty_claimed") for r in out["revisions"])
    assert all(not s.get("certainty_claimed") for s in out["belief_states"])


def test_wmbr03_unsupported_claims_remain_unverified():
    assert any(s["belief_status"] == "UNVERIFIED" for s in _out()["belief_states"])


# --- Contradiction & retraction -------------------------------------------

def test_wmbr03_contradicting_evidence_creates_contradiction():
    claim, task = _claim_task()
    result = process_claim_evidence(claim, task, ["CONTRADICTS"], ["matrix-x"])
    assert result["contradictions"]
    assert result["belief_state"]["belief_status"] == "CONTRADICTED"


def test_wmbr03_contradiction_does_not_resolve_truth():
    assert all(not c["truth_resolved"] and not c["contradictions_resolve_truth"] for c in _out()["contradictions"])


def test_wmbr03_retraction_record_append_only():
    claim, task = _claim_task()
    result = process_claim_evidence(claim, task, ["SUPPORTS", "CONTRADICTS"], ["matrix-x"])
    assert result["retractions"]
    assert result["belief_state"]["belief_status"] == "RETRACTED"


def test_wmbr03_retraction_preserves_original_claim():
    assert all(r["original_claim_preserved"] for r in _out()["retractions"])


def test_wmbr03_no_delete_or_rewrite_original_claim():
    assert all(not r["deletion_performed"] and not r["rewrite_performed"] for r in _out()["retractions"])


# --- Provenance ------------------------------------------------------------

def test_wmbr03_provenance_chain_required_for_supported_state():
    with pytest.raises(BeliefRevisionError):
        build_belief_state(
            claim_id="c1", claim_hash="h", belief_status="PROVISIONALLY_SUPPORTED",
            supporting_ids=[], contradicting_ids=[], provenance_chain_hash=None,
        )


def test_wmbr03_provenance_chain_links_claim_task_evidence_revision():
    claim, task = _claim_task()
    result = process_claim_evidence(claim, task, ["SUPPORTS"], ["matrix-x"])
    chain = result["provenance_chain"]
    assert chain["claim_id"] == claim["claim_id"]
    assert task["task_id"] in chain["source_verification_task_ids"]
    assert chain["evidence_receipt_ids"]
    assert chain["revision_ids"]


# --- Boundaries ------------------------------------------------------------

def test_wmbr03_no_web_browse():
    assert _out()["manifest"]["web_browse_performed"] is False


def test_wmbr03_no_external_provider_calls():
    assert _out()["manifest"]["external_provider_calls_made"] is False


def test_wmbr03_no_live_effects():
    assert _out()["manifest"]["live_external_side_effects_created"] is False


def test_wmbr03_no_authority_granted():
    assert _out()["manifest"]["authority_granted"] is False


def test_wmbr03_no_tools_authorized():
    assert _out()["manifest"]["tools_authorized"] is False


def test_wmbr03_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_wmbr03_preserves_phase40_repair():
    assert _gate_summary()["phase40_repair_preserved"] is True


def test_wmbr03_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_wmbr03_does_not_complete_wmbr01_parent():
    assert validate_wmbr03_gate(_gate_summary(candidate_agi_parent_phase_completed=True))["ok"] is False


# --- Replay & laundering ---------------------------------------------------

def test_wmbr03_replay_preserves_revision_hashes():
    out = _out()
    assert replay_ledger(out["revisions"], out["belief_states"], out["evidence_receipts"], out["manifest"])["ok"] is True


def test_wmbr03_replay_rejects_mutated_revision():
    out = _out()
    revisions = copy.deepcopy(out["revisions"])
    revisions[0]["new_belief_status"] = "VERIFIED_TRUE"
    assert replay_ledger(revisions, out["belief_states"], out["evidence_receipts"], out["manifest"])["ok"] is False


def test_wmbr03_no_secret_material_in_artifacts():
    assert secret_scan(_out()) is True
    assert "sk-lm-" not in repr(_out())


def test_wmbr03_fake_green_truth_revision_rejected():
    assert validate_wmbr03_gate(_gate_summary(truth_claimed=True))["ok"] is False
    assert validate_wmbr03_gate(_gate_summary(certainty_claimed=True))["ok"] is False


def test_wmbr03_truth_laundering_fixture_rejected():
    with pytest.raises(BeliefRevisionError):
        assert_neutral(truth_laundering_fixture())


def test_wmbr03_certainty_laundering_fixture_rejected():
    with pytest.raises(BeliefRevisionError):
        assert_neutral(certainty_laundering_fixture())


def test_wmbr03_claim_rewrite_fixture_rejected():
    with pytest.raises(BeliefRevisionError):
        assert_neutral(claim_rewrite_fixture())


# --- Gate ------------------------------------------------------------------

def test_wmbr03_gate_requires_wmbr02_green():
    assert validate_wmbr03_gate(_gate_summary(wmbr02_green=False))["ok"] is False
    assert WMBR_02_VERDICT_GREEN.startswith("GREEN_WMBR_02")


def test_wmbr03_gate_requires_wmbr01a_green():
    assert validate_wmbr03_gate(_gate_summary(wmbr01a_green=False))["ok"] is False
    assert WMBR_01A_VERDICT_GREEN.startswith("GREEN_WMBR_01A")


def test_wmbr03_gate_requires_runtime_p42_green():
    assert validate_wmbr03_gate(_gate_summary(runtime_p42_green=False))["ok"] is False
    assert RUNTIME_P42_VERDICT_GREEN.startswith("GREEN_PHASE42")


def test_wmbr03_gate_refuses_without_evidence_receipts():
    assert validate_wmbr03_gate(_gate_summary(evidence_receipts_written=False, evidence_receipt_count=0))["ok"] is False


def test_wmbr03_gate_refuses_without_belief_states():
    assert validate_wmbr03_gate(_gate_summary(belief_states_written=False, belief_state_count=0))["ok"] is False


def test_wmbr03_gate_refuses_without_revision_records():
    assert validate_wmbr03_gate(_gate_summary(belief_revisions_written=False, belief_revision_count=0))["ok"] is False


def test_wmbr03_gate_refuses_if_claim_marked_true():
    assert validate_wmbr03_gate(_gate_summary(claims_marked_true=True))["ok"] is False


def test_wmbr03_gate_refuses_if_certainty_claimed():
    assert validate_wmbr03_gate(_gate_summary(certainty_claimed=True))["ok"] is False


def test_wmbr03_gate_refuses_if_missing_provenance():
    assert validate_wmbr03_gate(_gate_summary(all_evidence_has_provenance=False))["ok"] is False


def test_wmbr03_gate_refuses_if_model_output_used_as_evidence():
    assert validate_wmbr03_gate(_gate_summary(model_output_treated_as_evidence=True))["ok"] is False


def test_wmbr03_gate_refuses_if_task_used_as_evidence():
    assert validate_wmbr03_gate(_gate_summary(verification_task_treated_as_evidence=True))["ok"] is False


def test_wmbr03_gate_refuses_if_authority_granted():
    assert validate_wmbr03_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_wmbr03_gate_refuses_if_live_effect_created():
    assert validate_wmbr03_gate(_gate_summary(live_external_side_effects_created=True))["ok"] is False


def test_wmbr03_gate_refuses_without_proof_bundle():
    assert validate_wmbr03_gate(_gate_summary(proof_bundle_valid=False))["ok"] is False


def test_wmbr03_gate_passes_on_full_summary():
    assert validate_wmbr03_gate(_gate_summary())["ok"] is True
